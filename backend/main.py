"""Qubitrail FastAPI application; serves web UI and REST API."""
from __future__ import annotations
import os
import traceback
import sys
from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from . import quantum as q, store
from .library import public_templates
from .guide import respond
from .research import repair_suite
from . import qiskit_bridge

# Don't take the whole API offline if ephemeral SQLite fails to initialize.
# Storage operations will report their own errors; core simulation can remain usable.
try:
    store.init()
except Exception as exc:
    print(f"Qubitrail: SQLite initialization failed: {type(exc).__name__}: {exc}", file=sys.stderr)

app=FastAPI(title='Qubitrail Quantum Studio API',version='1.0.0',docs_url='/api/docs',openapi_url='/api/openapi.json')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_credentials=False,allow_methods=['*'],allow_headers=['*'])

class CircuitIn(BaseModel):
    circuit:dict[str,Any]
    shots:int=Field(default=512,ge=1,le=4096)
    seed:int=42

class InspectIn(BaseModel):
    circuit:dict[str,Any]
    spec:dict[str,Any]=Field(default_factory=lambda:{'target':'bell_phi_plus'})
    maxCandidates:int=Field(default=400,ge=1,le=1200)

class VerifyIn(BaseModel):
    circuit:dict[str,Any]
    reference:dict[str,Any]
    mode:str='unitary'

class NoiseIn(BaseModel):
    circuit:dict[str,Any]
    shots:int=Field(default=512,ge=1,le=4096)
    noise:dict[str,float]=Field(default_factory=dict)
    seed:int=42

class ProjectIn(BaseModel):
    name:str='Untitled Circuit'
    description:str=''
    circuit:dict[str,Any]

class QasmIn(BaseModel):
    source:str

class ExportIn(BaseModel):
    circuit:dict[str,Any]
    format:str='qasm'

class GuideIn(BaseModel):
    message:str
    circuit:dict[str,Any]

@app.exception_handler(q.CircuitError)
async def circuit_error_handler(request,exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400,content={'detail':str(exc)})

@app.get('/api/health')
def health():return {'status':'healthy','project':'Qubitrail','engine':'NumPy quantum simulation','maxQubits':q.MAX_QUBITS,'database':'Ephemeral SQLite (Vercel)' if os.environ.get('VERCEL') else 'SQLite (local)','hardwareRequired':False}

@app.get('/api/qiskit/status')
def qiskit_status():return qiskit_bridge.status()

@app.post('/api/qiskit/simulate')
def qiskit_run(body:CircuitIn):return qiskit_bridge.simulate_qiskit(body.circuit,body.shots)

@app.get('/api/catalog')
def catalog():return {'gates':{'single':q.SINGLE,'double':q.DOUBLE,'triple':q.TRIPLE,'special':q.SPECIAL,'parametric':q.PARAMETRIC},'maxQubits':q.MAX_QUBITS,'maxGates':q.MAX_GATES,'features':['Circuit design','statevector simulation','sampled measurements','Bloch vectors','state fidelity','single-edit repair','unitary verification','local circuit optimization','noisy quantum trajectories','project history','OpenQASM 2 import/export','Qiskit Python export','experiment benchmarking','offline rule-based quantum guide']}

@app.get('/api/templates')
def templates():return public_templates()

@app.post('/api/steps')
def steps(body:CircuitIn):return q.trace_states(body.circuit)

@app.post('/api/repair-suite')
def run_repair_suite():
    result=repair_suite()
    store.add_experiment('repair-suite',{'cases':result['total'],'repaired':result['repaired'],'successRate':result['successRate'],'localizationRate':result['localizationRate']})
    return result

@app.post('/api/simulate')
def simulate(body:CircuitIn):return q.simulate(body.circuit,body.shots,seed=body.seed)

@app.post('/api/noise')
def noise(body:NoiseIn):
    result=q.simulate(body.circuit,body.shots,noise=body.noise,seed=body.seed)
    result['baseline']=q.simulate(body.circuit,body.shots,seed=body.seed)['counts']
    return result

@app.post('/api/debug')
def debug(body:InspectIn):return q.inspect(body.circuit,body.spec)

@app.post('/api/repair')
def repair(body:InspectIn):
    result=q.repair(body.circuit,body.spec,body.maxCandidates)
    store.add_experiment('repair',{'fidelityBefore':result['original']['fidelity'],'evaluated':result['evaluated'],'bestFidelity':result['suggestions'][0]['fidelity'] if result['suggestions'] else result['original']['fidelity']})
    return result

@app.post('/api/verify')
def verify(body:VerifyIn):
    if body.mode not in ('state','unitary'):raise q.CircuitError('Verification mode must be state or unitary.')
    return q.verify(body.circuit,body.reference,body.mode)

@app.post('/api/optimize')
def optimize(body:CircuitIn):
    result=q.optimize(body.circuit)
    store.add_experiment('optimization',{'before':result['before'],'after':result['after'],'verified':result['verification'].get('equivalent')})
    return result

@app.post('/api/benchmark')
def benchmark(body:CircuitIn):
    result=q.benchmark(body.circuit,body.shots)
    store.add_experiment('benchmark',result)
    return result

@app.post('/api/import/qasm')
def import_qasm(body:QasmIn):return q.from_qasm(body.source)

@app.post('/api/export')
def export_circuit(body:ExportIn):
    if body.format=='qasm':source=q.to_qasm(body.circuit)
    elif body.format=='python':source=q.to_qiskit(body.circuit)
    else:raise q.CircuitError('Export format must be qasm or python.')
    return {'format':body.format,'source':source}

@app.get('/api/projects')
def projects():return store.list_projects()

@app.post('/api/projects')
def create_project(body:ProjectIn):
    clean=q.validate(body.circuit)
    return store.save_project({**body.model_dump(),'circuit':clean})

@app.get('/api/projects/{pid}')
def project(pid:str):
    item=store.get_project(pid)
    if item is None:raise HTTPException(404,'Project not found.')
    return item

@app.put('/api/projects/{pid}')
def update_project(pid:str,body:ProjectIn):
    clean=q.validate(body.circuit)
    item=store.save_project({**body.model_dump(),'circuit':clean},pid)
    if item is None:raise HTTPException(404,'Project not found.')
    return item

@app.delete('/api/projects/{pid}')
def delete_project(pid:str):
    if not store.delete_project(pid):raise HTTPException(404,'Project not found.')
    return {'deleted':True}

@app.get('/api/projects/{pid}/versions')
def history(pid:str):
    if store.get_project(pid) is None:raise HTTPException(404,'Project not found.')
    return store.versions(pid)

@app.get('/api/experiments')
def experiments(limit:int=50):return store.list_experiments(limit)

@app.post('/api/guide')
def guide(body:GuideIn):return respond(body.message,q.validate(body.circuit))

ROOT = Path(__file__).resolve().parent.parent
FRONT = ROOT / 'frontend'
if not FRONT.is_dir():
    FRONT = ROOT / 'public'
if FRONT.is_dir():
    app.mount('/assets',StaticFiles(directory=(FRONT / 'assets') if (FRONT / 'assets').is_dir() else FRONT),name='assets')
@app.get('/')
def home():
    index = FRONT/'index.html'
    if not index.is_file():
        raise HTTPException(503, 'Frontend files are missing from the deployed function.')
    return FileResponse(index)
@app.get('/{path:path}',include_in_schema=False)
def spa_fallback(path:str):
    # No accidental HTML for missing API calls.
    if path.startswith('api/'):raise HTTPException(404,'Endpoint not found.')
    index = FRONT/'index.html'
    if not index.is_file():
        raise HTTPException(503, 'Frontend files are missing from the deployed function.')
    return FileResponse(index)
