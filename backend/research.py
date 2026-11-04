"""Deterministic injected-fault benchmark, designed to be reproducible rather than cherry-picked."""
from . import quantum as q
from .library import public_templates

CASES = [
    {'id':'bell_controlled_type','template':'bell','gate':1,'replacement':'CZ','target':'bell_phi_plus'},
    {'id':'bell_hadamard_type','template':'bell','gate':0,'replacement':'X','target':'bell_phi_plus'},
    {'id':'bell_minus_phase','template':'bell_minus','gate':2,'replacement':'X','target':'bell_phi_minus'},
    {'id':'ghz_entangler','template':'ghz','gate':1,'replacement':'CZ','target':'ghz'},
    {'id':'uniform_hadamard','template':'superposition','gate':1,'replacement':'Z','target':'uniform'},
    {'id':'ghz_missing_entangler','template':'ghz','gate':2,'replacement':'SWAP','target':'ghz'},
]

def repair_suite(max_cases=6):
    templates={t['id']:t for t in public_templates()}
    results=[]
    for case in CASES[:max(1,min(int(max_cases),len(CASES)))]:
        item=templates[case['template']]
        faulty={'name':'Fault benchmark / '+case['id'],'qubits':item['qubits'],'gates':[dict(g) for g in item['gates']]}
        op=dict(faulty['gates'][case['gate']]);op['type']=case['replacement'];op.pop('angle',None);faulty['gates'][case['gate']]=op
        out=q.repair(faulty,{'target':case['target']},max_candidates=700)
        correct=next((s for s in out['suggestions'] if s['passed']),None)
        results.append({'id':case['id'],'template':item['name'],'injectedGate':case['gate']+1,'faultType':case['replacement'], 'originalFidelity':out['original']['fidelity'],'repaired':correct is not None,'bestFidelity':correct['fidelity'] if correct else max([s['fidelity'] for s in out['suggestions']],default=out['original']['fidelity']),'localized':bool(correct and correct['changedIndex']==case['gate']),'candidatesEvaluated':out['evaluated'],'bestRepair':correct['description'] if correct else None})
    solved=sum(r['repaired'] for r in results)
    return {'cases':results,'total':len(results),'repaired':solved,'successRate':round(solved/len(results),5),'localizationRate':round(sum(r['localized'] for r in results)/len(results),5),'description':'Fixed six-case, deterministic, injected single-gate fault benchmark. This small illustrative dataset is not evidence of general repair performance.'}
