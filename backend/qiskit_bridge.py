"""Optional IBM Qiskit Aer integration. The native NumPy backend works without this."""
from .quantum import validate,PARAMETRIC,CircuitError

def status():
    try:
        import qiskit
        import qiskit_aer
        return {'installed':True,'qiskitVersion':getattr(qiskit,'__version__','unknown'),'aerVersion':getattr(qiskit_aer,'__version__','unknown')}
    except ImportError:
        return {'installed':False,'detail':'Optional Qiskit integration not installed. Run pip install -r requirements-optional-quantum.txt to enable it.'}

def simulate_qiskit(raw,shots=512):
    try:
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator
    except ImportError as exc:
        raise CircuitError('Qiskit Aer is optional and not installed. Install requirements-optional-quantum.txt.') from exc
    c=validate(raw);qc=QuantumCircuit(c['qubits'],c['qubits']);measured=set()
    for g in c['gates']:
        t=g['type'];targets=g['targets'];args=[int(i) for i in targets]
        if t=='MEASURE':qc.measure(args[0],args[0]);measured.add(args[0])
        elif t=='RESET':qc.reset(args[0])
        elif t=='BARRIER':qc.barrier(*(args or list(range(c['qubits']))))
        else:
            try:
                if t in PARAMETRIC:getattr(qc,t.lower())(float(g['angle']),*args)
                else:getattr(qc,t.lower())(*args)
            except (AttributeError,TypeError) as exc:
                raise CircuitError(f'Qiskit backend does not support gate {t} in this installation.') from exc
    for i in range(c['qubits']):
        if i not in measured:qc.measure(i,i)
    try:
        counts=AerSimulator().run(qc,shots=shots).result().get_counts()
    except Exception as exc:
        raise CircuitError(f'Qiskit execution failed: {str(exc)[:200]}') from exc
    return {'backend':'IBM Qiskit Aer (optional)','shots':shots,'counts':dict(sorted(counts.items())),'circuit':c}
