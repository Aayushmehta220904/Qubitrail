import math
import numpy as np
import pytest
from backend import quantum as q
from backend.library import public_templates

def template(key):return next(t['circuit'] for t in public_templates() if t['id']==key)

def test_bell_probabilities():
    s=q.simulate(template('bell'),256)
    ideal={p['state']:p['probability'] for p in s['idealProbabilities']}
    assert ideal=={'00':.5,'11':.5}
    assert s['metrics']['twoQubitGates']==1

def test_bell_state_minus_has_relative_phase():
    assert q.fidelity(q.pure_state(template('bell')),q.pure_state(template('bell_minus')))<1e-8
    assert q.simulate(template('bell_minus'),128)['idealProbabilities']==q.simulate(template('bell'),128)['idealProbabilities']

def test_bell_target():assert q.inspect(template('bell'),{'target':'bell_phi_plus'})['passed']
def test_ghz_target():assert q.inspect(template('ghz'),{'target':'ghz'})['passed']
def test_grover_search():assert q.simulate(template('grover'),128)['counts']=={'11':128}
def test_bv_secret():
    out=q.simulate(template('bv'),200)['counts']
    assert set(s[-3:] for s in out)=={'101'}

def test_teleportation_output_qubit():
    s=q.pure_state(template('teleport'))
    b=q.bloch(s,2,3)
    assert b['z']==pytest.approx(math.cos(.8),abs=1e-6)
    assert b['x']==pytest.approx(math.sin(.8),abs=1e-6)

def test_entangled_reduced_state_purity():assert q.bloch(q.pure_state(template('bell')),0,2)['purity']==pytest.approx(.5,abs=1e-6)

def test_compose_hh_equals_identity():
    cir={'qubits':1,'gates':[{'type':'H','targets':[0]},{'type':'H','targets':[0]}]}
    assert q.verify(cir,{'qubits':1,'gates':[]})['equivalent']

def test_cx_direction_matters():
    c={'qubits':2,'gates':[{'type':'X','targets':[0]},{'type':'CX','targets':[0,1]}]}
    assert q.simulate(c,128)['counts']=={'11':128}
    c['gates'][1]['targets']=[1,0]
    assert q.simulate(c,128)['counts']=={'01':128}

def test_auto_repair_broken_bell():
    out=q.repair(template('repair_demo'),{'target':'bell_phi_plus'})
    assert out['original']['fidelity']<.3
    assert out['suggestions'][0]['passed']
    assert q.inspect(out['suggestions'][0]['circuit'],{'target':'bell_phi_plus'})['passed']

def test_optimizer_verified():
    c=template('opt_demo');r=q.optimize(c)
    assert r['after']['gates']<r['before']['gates']
    assert r['verification']['equivalent']
    assert q.verify(c,r['circuit'])['equivalent']

def test_optimize_crx_2pi_not_cancelled():
    c={'qubits':2,'gates':[{'type':'CRX','targets':[0,1],'angle':math.pi},{'type':'CRX','targets':[0,1],'angle':math.pi}]}
    r=q.optimize(c)
    assert r['after']['gates']==1
    assert r['verification']['equivalent']
    assert not q.verify(c,{'qubits':2,'gates':[]})['equivalent']

def test_zero_noise_reproducible():
    c=template('bell');a=q.simulate(c,256,seed=21);b=q.simulate(c,256,seed=21)
    assert a['counts']==b['counts']

def test_noisy_trajectories():
    c={'qubits':1,'gates':[{'type':'X','targets':[0]}]}
    out=q.simulate(c,128,noise={'readout':1.0})
    assert out['counts']=={'0':128}

def test_measure_and_reset():
    c={'qubits':1,'gates':[{'type':'X','targets':[0]},{'type':'MEASURE','targets':[0]},{'type':'RESET','targets':[0]}]}
    s=q.simulate(c,100)
    assert s['counts']=={'1':100}  # Final output retains explicit measurement result.
    assert s['mixed']

def test_global_phase_accepted():
    a={'qubits':1,'gates':[{'type':'RX','targets':[0],'angle':2*math.pi}]}
    b={'qubits':1,'gates':[]}
    assert q.verify(a,b)['equivalent']

def test_state_equivalent_not_unitary():
    a={'qubits':1,'gates':[{'type':'Z','targets':[0]}]}
    b={'qubits':1,'gates':[]}
    assert q.verify(a,b,'state')['equivalent']
    assert not q.verify(a,b,'unitary')['equivalent']

def test_qasm_roundtrip():
    c=template('qft');qasm=q.to_qasm(c);d=q.from_qasm(qasm)
    assert q.verify(c,d)['equivalent']

def test_qasm_dangerous_expression_rejected():
    with pytest.raises(q.CircuitError):q.parse_angle('__import__("os").system("pwd")')

def test_bad_gate_rejected():
    with pytest.raises(q.CircuitError):q.validate({'qubits':2,'gates':[{'type':'LOL','targets':[0]}]})

def test_bad_target_rejected():
    with pytest.raises(q.CircuitError):q.validate({'qubits':2,'gates':[{'type':'CX','targets':[0,0]}]})

def test_limit_qubits():
    with pytest.raises(q.CircuitError):q.validate({'qubits':15,'gates':[]})

def test_noisy_work_limit():
    c={'qubits':8,'gates':[{'type':'X','targets':[0]}]*150}
    with pytest.raises(q.CircuitError):q.simulate(c,4096,noise={'readout':.1})

def test_all_templates_simulate():
    for t in public_templates():
        assert q.simulate(t['circuit'],8)['metrics']['qubits']==t['qubits']

def test_qiskit_code_exports():
    text=q.to_qiskit(template('bell'))
    assert 'qc.cx(0, 1)' in text and 'AerSimulator' in text

def test_api_endpoints():
    from fastapi.testclient import TestClient
    from backend.main import app
    client=TestClient(app)
    assert client.get('/api/health').status_code==200
    assert len(client.get('/api/templates').json())>=14
    assert client.get('/').status_code==200
    assert client.get('/assets/app.js').status_code==200
    c=template('repair_demo')
    r=client.post('/api/repair',json={'circuit':c,'spec':{'target':'bell_phi_plus'}})
    assert r.status_code==200 and r.json()['suggestions'][0]['passed']
    assert client.post('/api/verify',json={'circuit':template('bell'),'reference':template('bell')}).json()['equivalent']
    assert client.post('/api/import/qasm',json={'source':q.to_qasm(template('bell'))}).status_code==200
    assert client.post('/api/noise',json={'circuit':template('bell'),'shots':100,'noise':{'readout':.01}}).status_code==200
    assert client.post('/api/guide',json={'message':'Explain phase','circuit':template('bell')}).status_code==200

def test_projects_crud():
    from fastapi.testclient import TestClient
    from backend.main import app
    client=TestClient(app)
    c=template('bell')
    r=client.post('/api/projects',json={'name':'Test integration project','circuit':c});assert r.status_code==200
    pid=r.json()['id']
    try:
        assert client.get('/api/projects/'+pid).status_code==200
        assert len(client.get('/api/projects/'+pid+'/versions').json())==1
        assert client.put('/api/projects/'+pid,json={'name':'Updated name','circuit':c}).status_code==200
        assert len(client.get('/api/projects/'+pid+'/versions').json())==2
    finally:
        assert client.delete('/api/projects/'+pid).status_code==200
    assert client.get('/api/projects/'+pid).status_code==404

def test_stepwise_timeline():
    result=q.trace_states(template('bell'))
    assert result['total']==3
    assert result['steps'][0]['probabilities']==[{'state':'00','probability':1.0}]
    assert {x['state']:x['probability'] for x in result['steps'][-1]['probabilities']}=={'00':0.5,'11':0.5}

def test_stepwise_rejects_midcircuit_measure():
    with pytest.raises(q.CircuitError):q.trace_states({'qubits':1,'gates':[{'type':'MEASURE','targets':[0]}]})

def test_deterministic_repair_suite():
    from backend.research import repair_suite
    a=repair_suite();b=repair_suite()
    assert a==b
    assert a['total']==6 and a['repaired']>=4

def test_new_research_endpoints():
    from fastapi.testclient import TestClient
    from backend.main import app
    client=TestClient(app)
    assert client.post('/api/steps',json={'circuit':template('bell')}).json()['total']==3
    assert client.post('/api/repair-suite',json={}).json()['total']==6
    status=client.get('/api/qiskit/status').json()
    assert 'installed' in status
    if not status['installed']:
        assert client.post('/api/qiskit/simulate',json={'circuit':template('bell')}).status_code==400
