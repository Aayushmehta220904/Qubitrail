"""Transparent, offline expert guide (not represented as an LLM)."""
from .quantum import metrics

def respond(message,circuit):
    msg=(message or '').lower().strip();m=metrics(circuit)
    facts=f'Your circuit has {m["qubits"]} qubits, {m["gates"]} operations, depth {m["depth"]}, and {m["twoQubitGates"]} multi-qubit operations.'
    if any(w in msg for w in ('repair','fix','bug','wrong','debug')):
        answer=f'{facts} Open the Debug & Repair tab, select the expected target (or reference circuit), then run Diagnose or Auto Repair. Repairs are bounded searches over gate changes; every candidate is checked against the target state. Without an expected behaviour specification, a circuit cannot be classified as incorrect.'
    elif any(w in msg for w in ('optimi','faster','shorter','depth','gate count')):
        answer=f'{facts} Optimization cancels adjacent inverse gates and merges supported rotations. The new circuit is checked for equivalence; reductions are not guaranteed. Use the Optimizer tab to see before-and-after metrics.'
    elif 'bell' in msg or 'entangle' in msg:
        answer='To prepare |Φ+⟩=(|00⟩+|11⟩)/√2, start with |00⟩, apply H to q0, then CX(q0,q1). Each ideal measurement outcome 00 and 11 has probability 1/2. Use the Bell State template or the deliberately broken Bell template for repair.'
    elif 'phase' in msg:
        answer='A relative phase changes interference even when measurement probabilities are initially unchanged. Z|+⟩=|−⟩; global phase is physically unobservable. You can inspect amplitude phase in the State view and verify full unitary equivalence on up to five qubits.'
    elif 'noise' in msg or 'error' in msg:
        answer='Use the Noise Lab to apply depolarizing, bit-flip, phase-flip, amplitude-damping and readout noise. The simulator samples stochastic quantum trajectories; increasing the number of shots reduces sampling uncertainty but does not eliminate noise.'
    elif 'qasm' in msg or 'export' in msg or 'python' in msg:
        answer='Open Code / Import in the Studio. Export OpenQASM 2.0 or generated Qiskit Python; QASM 2.0 import handles the supported gate subset. Qiskit Python export requires the external qiskit and qiskit-aer packages to execute.'
    elif 'verify' in msg or 'equivalent' in msg:
        answer='Two circuits can be state-equivalent from |0…0⟩ without being the same unitary. Full-unitary verification compares every basis input, up to global phase, and is available for up to five qubits. State verification supports up to eight.'
    elif 'grover' in msg:
        answer='Grover search uses an oracle that changes the phase of marked states and a diffusion step that amplifies their amplitudes. The built-in two-qubit example marks |11⟩; run it and check its measured outcome probabilities.'
    elif 'teleport' in msg:
        answer='Quantum teleportation transfers an unknown qubit state using entanglement and classical communication. The included tutorial uses a coherent deferred-measurement construction, replacing classical feed-forward with controlled quantum corrections.'
    elif 'bloch' in msg:
        answer='The Bloch vector (x,y,z) represents the reduced state of one qubit. For entangled multi-qubit states, a single qubit may be mixed, so its Bloch vector can lie inside the sphere. Open Simulation → Bloch vectors.'
    else:
        answer=f'{facts} I am an offline, rule-based quantum guide rather than a generative AI model. I can explain Bell states, phase, gates, debugging and repair, optimization, equivalence, noise, teleportation, Grover, QASM, and the Bloch sphere. For circuit-specific mathematical results use the relevant verified engine tab.'
    return {'reply':answer,'mode':'Offline rule-based expert guide','suggestions':['How can I repair a Bell circuit?','Explain phase and global phase','How does equivalence checking work?']}
