"""Working, educational circuit templates, all executable with the built-in simulator."""
import math

def G(t,*q,angle=None):
    g={'type':t,'targets':list(q)}
    if angle is not None:g['angle']=angle
    return g

TEMPLATES=[
 {'id':'bell','name':'Bell State | Φ+','category':'Entanglement','level':'Beginner','summary':'Create maximally entangled qubits with H and CX.','qubits':2,'gates':[G('H',0),G('CX',0,1)],'target':'bell_phi_plus'},
 {'id':'bell_minus','name':'Bell State | Φ−','category':'Entanglement','level':'Beginner','summary':'Bell state with a relative phase flip.','qubits':2,'gates':[G('H',0),G('CX',0,1),G('Z',0)],'target':'bell_phi_minus'},
 {'id':'ghz','name':'GHZ Three-Qubit State','category':'Entanglement','level':'Intermediate','summary':'Three-partite entanglement with one H and two CX operations.','qubits':3,'gates':[G('H',0),G('CX',0,1),G('CX',1,2)],'target':'ghz'},
 {'id':'superposition','name':'Equal Superposition','category':'Foundations','level':'Beginner','summary':'Apply Hadamards to create a uniform amplitude distribution.','qubits':3,'gates':[G('H',0),G('H',1),G('H',2)],'target':'uniform'},
 {'id':'phase_kickback','name':'Phase Kickback','category':'Algorithms','level':'Intermediate','summary':'Explore conditional phases in a control-target system.','qubits':2,'gates':[G('H',0),G('X',1),G('H',1),G('CX',0,1),G('H',0)]},
 {'id':'deutsch','name':'Deutsch Algorithm — Balanced','category':'Algorithms','level':'Intermediate','summary':'A one-query demonstration with the balanced oracle f(x)=x.','qubits':2,'gates':[G('X',1),G('H',0),G('H',1),G('CX',0,1),G('H',0)]},
 {'id':'dj','name':'Deutsch–Jozsa — 3 Input Qubits','category':'Algorithms','level':'Intermediate','summary':'Balanced parity oracle (x0 XOR x1 XOR x2). Output 000 is absent on the input register.','qubits':4,'gates':[G('X',3),*[G('H',i) for i in range(4)],*[G('CX',i,3) for i in range(3)],*[G('H',i) for i in range(3)]]},
 {'id':'bv','name':'Bernstein–Vazirani — Secret 101','category':'Algorithms','level':'Intermediate','summary':'Retrieve secret bit string 101 from a phase oracle.','qubits':4,'gates':[G('X',3),*[G('H',i) for i in range(4)],G('CX',0,3),G('CX',2,3),*[G('H',i) for i in range(3)]]},
 {'id':'grover','name':'Grover Search — Mark |11⟩','category':'Algorithms','level':'Advanced','summary':'Two-qubit amplitude amplification for the marked state 11.','qubits':2,'gates':[G('H',0),G('H',1),G('CZ',0,1),G('H',0),G('H',1),G('X',0),G('X',1),G('CZ',0,1),G('X',0),G('X',1),G('H',0),G('H',1)]},
 {'id':'qft','name':'Quantum Fourier Transform (3q)','category':'Algorithms','level':'Advanced','summary':'Three-qubit QFT with controlled phase rotations and bit reversal.','qubits':3,'gates':[G('H',2),G('CP',1,2,angle=math.pi/2),G('CP',0,2,angle=math.pi/4),G('H',1),G('CP',0,1,angle=math.pi/2),G('H',0),G('SWAP',0,2)]},
 {'id':'teleport','name':'Coherent Quantum Teleportation','category':'Protocols','level':'Advanced','summary':'Deferred-measurement teleportation circuit; q2 receives the original q0 state without feed-forward measurement.','qubits':3,'gates':[G('RY',0,angle=.8),G('H',1),G('CX',1,2),G('CX',0,1),G('H',0),G('CZ',0,2),G('CX',1,2)]},
 {'id':'superdense','name':'Superdense Coding — Message 10','category':'Protocols','level':'Intermediate','summary':'Encode two classical bits through an entangled pair, then decode.','qubits':2,'gates':[G('H',0),G('CX',0,1),G('Z',0),G('CX',0,1),G('H',0)]},
 {'id':'toffoli','name':'Toffoli Controlled-Controlled-X','category':'Foundations','level':'Beginner','summary':'Two controls flip a third target.','qubits':3,'gates':[G('X',0),G('X',1),G('CCX',0,1,2)]},
 {'id':'noise_demo','name':'Noise Sensitivity Playground','category':'Noise','level':'Intermediate','summary':'A longer circuit with repeated operations for comparative noisy simulation.','qubits':3,'gates':[G('H',0),G('CX',0,1),G('CX',1,2),G('RZ',0,angle=math.pi/3),G('RX',1,angle=math.pi/4),G('CX',0,2),G('H',1),G('CX',1,2),G('RY',2,angle=math.pi/6)]},
 {'id':'repair_demo','name':'Broken Bell State — Repair Me','category':'Debugging','level':'Beginner','summary':'Deliberately incorrect Bell-state preparation: use Repair to find the CZ/CX defect.','qubits':2,'gates':[G('H',0),G('CZ',0,1)],'target':'bell_phi_plus'},
 {'id':'opt_demo','name':'Redundant Gates — Optimize Me','category':'Optimization','level':'Beginner','summary':'Multiple cancelling gates and adjacent rotations; simplify and verify.','qubits':2,'gates':[G('H',0),G('H',0),G('X',1),G('X',1),G('RX',0,angle=.3),G('RX',0,angle=.7),G('CX',0,1),G('CX',0,1),G('H',1)]},
]

def public_templates():
    return [{**t,'circuit':{'name':t['name'],'qubits':t['qubits'],'gates':t['gates']}} for t in TEMPLATES]
