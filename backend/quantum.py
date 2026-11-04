"""Small-circuit quantum simulator and numerical helpers. Qubit 0 is least-significant."""
from __future__ import annotations
import ast
import math
import re
from collections import Counter
from typing import Any
import numpy as np

MAX_QUBITS = 8
MAX_GATES = 180
SINGLE = ('I','X','Y','Z','H','S','SDG','T','TDG','SX','RX','RY','RZ','P')
DOUBLE = ('CX','CY','CZ','CH','SWAP','ISWAP','CP','CRX','CRY','CRZ','RZZ')
TRIPLE = ('CCX','CSWAP')
SPECIAL = ('MEASURE','RESET','BARRIER')
GATES = SINGLE + DOUBLE + TRIPLE + SPECIAL
PARAMETRIC = ('RX','RY','RZ','P','CP','CRX','CRY','CRZ','RZZ')
GATE_SYMBOLS = {g: g for g in GATES}

class CircuitError(ValueError):
    pass

def validate(circuit: dict) -> dict:
    if not isinstance(circuit, dict):
        raise CircuitError('Circuit must be a JSON object.')
    n = circuit.get('qubits', 2)
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= MAX_QUBITS:
        raise CircuitError(f'Number of qubits must be 1–{MAX_QUBITS}.')
    ops = circuit.get('gates', [])
    if not isinstance(ops, list) or len(ops)>MAX_GATES:
        raise CircuitError(f'Expected an array containing at most {MAX_GATES} gates.')
    cleaned=[]
    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            raise CircuitError(f'Gate {i+1} must be an object.')
        kind = str(op.get('type','')).upper().strip()
        if kind == 'CNOT': kind = 'CX'
        if kind == 'TOFFOLI': kind = 'CCX'
        if kind not in GATES:
            raise CircuitError(f'Unsupported gate at position {i+1}: {kind}.')
        targets = op.get('targets',[])
        if not isinstance(targets, list) or any(isinstance(x,bool) or not isinstance(x,int) or x<0 or x>=n for x in targets):
            raise CircuitError(f'Invalid qubit target at gate {i+1}.')
        arity = 1 if kind in SINGLE + ('MEASURE','RESET') else 2 if kind in DOUBLE else 3 if kind in TRIPLE else 0
        if kind == 'BARRIER':
            if len(set(targets)) != len(targets):
                raise CircuitError(f'Duplicate qubit at gate {i+1}.')
        elif len(targets) != arity or len(set(targets))!=len(targets):
            raise CircuitError(f'Gate {i+1} ({kind}) needs {arity} distinct qubit(s).')
        item={'type':kind,'targets':targets}
        if kind in PARAMETRIC:
            try: angle=float(op.get('angle',0.0))
            except (ValueError,TypeError): raise CircuitError(f'Invalid angle at gate {i+1}.')
            if not math.isfinite(angle): raise CircuitError('Gate angle must be finite.')
            item['angle']=angle
        cleaned.append(item)
    return {'qubits':n,'gates':cleaned,'name':str(circuit.get('name','Untitled Circuit'))[:120]}

def state_zero(n):
    s=np.zeros(2**n,dtype=np.complex128)
    s[0]=1
    return s

def fmt_complex(z: complex) -> dict:
    return {'re':float(np.real(z)),'im':float(np.imag(z)),'magnitude':float(abs(z)),'phase':float(np.angle(z))}

def matrix_for(op):
    kind=op['type']; theta=float(op.get('angle',0.0))
    I=np.eye(2,dtype=complex); X=np.array([[0,1],[1,0]],complex)
    Y=np.array([[0,-1j],[1j,0]],complex); Z=np.diag([1,-1]).astype(complex)
    H=np.array([[1,1],[1,-1]],complex)/np.sqrt(2)
    basis={'I':I,'X':X,'Y':Y,'Z':Z,'H':H,'S':np.diag([1,1j]),'SDG':np.diag([1,-1j]),'T':np.diag([1,np.exp(1j*np.pi/4)]),'TDG':np.diag([1,np.exp(-1j*np.pi/4)]),'SX':np.array([[1+1j,1-1j],[1-1j,1+1j]],complex)/2}
    if kind in basis: return basis[kind]
    if kind=='RX': return math.cos(theta/2)*I-1j*math.sin(theta/2)*X
    if kind=='RY': return math.cos(theta/2)*I-1j*math.sin(theta/2)*Y
    if kind=='RZ': return np.diag([np.exp(-1j*theta/2),np.exp(1j*theta/2)])
    if kind=='P': return np.diag([1,np.exp(1j*theta)])
    if kind in ('CX','CY','CZ','CH','CP','CRX','CRY','CRZ'):
        controlled = {'CX':'X','CY':'Y','CZ':'Z','CH':'H','CP':'P','CRX':'RX','CRY':'RY','CRZ':'RZ'}[kind]
        u=matrix_for({'type':controlled,'angle':theta})
        out=np.eye(4,dtype=complex)
        out[2:,2:]=u
        return out
    if kind=='RZZ': return np.diag([np.exp(-1j*theta/2),np.exp(1j*theta/2),np.exp(1j*theta/2),np.exp(-1j*theta/2)])
    if kind=='SWAP': return np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]],complex)
    if kind=='ISWAP': return np.array([[1,0,0,0],[0,0,1j,0],[0,1j,0,0],[0,0,0,1]],complex)
    if kind=='CCX':
        a=np.eye(8,dtype=complex);a[6,6]=a[7,7]=0;a[6,7]=a[7,6]=1;return a
    if kind=='CSWAP':
        a=np.eye(8,dtype=complex);a[5,5]=a[6,6]=0;a[5,6]=a[6,5]=1;return a
    return None

def apply_matrix(state: np.ndarray, targets: list[int], mat: np.ndarray, n: int) -> np.ndarray:
    """Ordered targets act as MSB ... LSB in the local matrix basis."""
    k=len(targets); masks=[1 << q for q in targets]; local_masks=[]
    for local in range(1<<k):
        local_masks.append(sum(mask for index,mask in enumerate(masks) if local & (1 << (k-1-index))))
    target_union=sum(masks)
    out=state.copy()
    for base in range(1<<n):
        if base & target_union: continue
        inds=[base|mask for mask in local_masks]
        out[inds]=mat@state[inds]
    return out

def measure_qubit(state, q, n, rng):
    mask=1<<q
    p1=float(sum(abs(state[i])**2 for i in range(len(state)) if i & mask))
    outcome=bool(rng.random()<p1)
    out=state.copy()
    for i in range(len(state)):
        if bool(i&mask)!=outcome: out[i]=0
    norm=np.linalg.norm(out)
    if norm>1e-12: out/=norm
    return out,int(outcome)

def run_trajectory(circuit, rng, noise=None):
    n=circuit['qubits']; state=state_zero(n)
    noise=noise or {}; strength=float(noise.get('depolarizing',0));bit=float(noise.get('bitFlip',0));phase=float(noise.get('phaseFlip',0)); damping=float(noise.get('amplitudeDamping',0))
    measured={}
    for gate in circuit['gates']:
        kind=gate['type'];t=gate['targets']
        if kind=='BARRIER':continue
        if kind=='MEASURE':
            state,outcome=measure_qubit(state,t[0],n,rng);measured[t[0]]=outcome;continue
        if kind=='RESET':
            state,outcome=measure_qubit(state,t[0],n,rng)
            if outcome:state=apply_matrix(state,t,matrix_for({'type':'X'}),n)
            continue
        state=apply_matrix(state,t,matrix_for(gate),n)
        for q in t:
            if strength>0 and rng.random()<strength:
                kind2=rng.choice(['X','Y','Z'])
                state=apply_matrix(state,[q],matrix_for({'type':kind2}),n)
            if bit>0 and rng.random()<bit:state=apply_matrix(state,[q],matrix_for({'type':'X'}),n)
            if phase>0 and rng.random()<phase:state=apply_matrix(state,[q],matrix_for({'type':'Z'}),n)
            if damping>0:
                p1=float(sum(abs(state[i])**2 for i in range(len(state)) if i & (1<<q)))
                jump_prob=min(1.,max(0.,damping*p1))
                if rng.random()<jump_prob:
                    mat=np.array([[0,np.sqrt(damping)],[0,0]],complex)
                else:
                    mat=np.diag([1.,np.sqrt(1.-damping)]).astype(complex)
                state=apply_matrix(state,[q],mat,n)
                norm=np.linalg.norm(state)
                if norm>1e-12:state/=norm
    if len(measured)==n:
        bits=''.join(str(measured[q]) for q in reversed(range(n)))
    else:
        # Existing measurement values are fixed; unmeasured qubits are read at end.
        probs=np.abs(state)**2; idx=int(rng.choice(len(state),p=probs/probs.sum()))
        bits=''.join(str(measured.get(q,(idx>>q)&1)) for q in reversed(range(n)))
    readout=float(noise.get('readout',0))
    if readout:
        chars=list(bits)
        for i in range(len(chars)):
            if rng.random()<readout:chars[i]='1' if chars[i]=='0' else '0'
        bits=''.join(chars)
    return state,bits

def pure_state(circuit):
    c=validate(circuit);s=state_zero(c['qubits'])
    for gate in c['gates']:
        if gate['type'] in ('MEASURE','RESET'):
            return None
        if gate['type']=='BARRIER':continue
        s=apply_matrix(s,gate['targets'],matrix_for(gate),c['qubits'])
    return s

def bitlabel(index,n): return format(index,f'0{n}b')

def bloch(state,q,n):
    if state is None:return None
    # rho01 = sum amplitude(bit=0) * conj(amplitude(bit=1))
    rho01=0j;p0=0.
    for i in range(len(state)):
        if not (i&(1<<q)):
            a=state[i];b=state[i|(1<<q)];p0+=abs(a)**2;rho01+=a*np.conj(b)
    x=2*float(rho01.real);y=-2*float(rho01.imag);z=2*float(p0)-1
    length=min(1.,float(np.sqrt(x*x+y*y+z*z)))
    purity=(1+length*length)/2
    p=(1+length)/2
    entropy=0 if p>=1-1e-12 else -(p*math.log2(p)+(1-p)*math.log2(1-p))
    return {'x':round(x,7),'y':round(y,7),'z':round(z,7),'purity':round(purity,7),'entropy':round(entropy,7),'radius':round(length,7)}

def metrics(circuit):
    c=validate(circuit);moments=[];last=[0]*c['qubits'];two=0
    for gate in c['gates']:
        if gate['type']=='BARRIER':continue
        targets=gate['targets'];lev=1+max([last[q] for q in targets],default=0)
        for q in targets:last[q]=lev
        moments.append(lev)
        if len(targets)>=2:two+=1
    return {'qubits':c['qubits'],'gates':len(c['gates']),'depth':max(moments,default=0),'twoQubitGates':two,'byGate':dict(Counter(g['type'] for g in c['gates']))}

def simulate(raw,shots=512,noise=None,seed=42):
    c=validate(raw);shots=int(shots)
    if shots<1 or shots>4096:raise CircuitError('Shots must be between 1 and 4096.')
    state=pure_state(c)
    rng=np.random.default_rng(int(seed))
    clean_noise={k:float((noise or {}).get(k,0)) for k in ['depolarizing','bitFlip','phaseFlip','amplitudeDamping','readout']}
    if any(not 0<=v<=1 or not math.isfinite(v) for v in clean_noise.values()):raise CircuitError('Noise probabilities must be between 0 and 1.')
    noisy=any(v>0 for v in clean_noise.values())
    nonunitary=state is None
    if (noisy or nonunitary) and shots*max(1,len(c['gates']))*(1<<c['qubits']) > 4_000_000:
        raise CircuitError('This noisy/measurement experiment is too large for the local simulator. Reduce qubits, gates or shots.')
    if not noisy and not nonunitary:
        prob=np.abs(state)**2
        indices=rng.choice(len(state),size=shots,p=prob/prob.sum())
        counts=Counter(bitlabel(int(i),c['qubits']) for i in indices)
    else:
        counts=Counter(run_trajectory(c,rng,clean_noise)[1] for _ in range(shots))
    ideal = [] if state is None else [{'state':bitlabel(i,c['qubits']),'probability':round(float(p),8)} for i,p in enumerate(np.abs(state)**2) if p>1e-9]
    values=[] if state is None else [{'state':bitlabel(i,c['qubits']),'re':round(float(v.real),8),'im':round(float(v.imag),8),'magnitude':round(float(abs(v)),8),'phase':round(float(np.angle(v)),8)} for i,v in enumerate(state) if abs(v)>1e-9]
    return {'circuit':c,'metrics':metrics(c),'shots':shots,'counts':dict(sorted(counts.items())),'probabilities':[{ 'state':bitlabel(i,c['qubits']),'probability':round(counts.get(bitlabel(i,c['qubits']),0)/shots,8)} for i in range(1<<c['qubits'])], 'idealProbabilities':ideal,'amplitudes':values,'bloch':[bloch(state,i,c['qubits']) for i in range(c['qubits'])], 'mixed':nonunitary or noisy,'noise':clean_noise,'simulation':'NumPy statevector / sampled quantum trajectories','qubitConvention':'q0 is the least-significant bit (rightmost displayed bit)'}

def fidelity(a,b):
    if a is None or b is None or a.shape!=b.shape:return None
    return float(min(1,abs(np.vdot(a,b))**2))

def state_for_spec(spec,n):
    if not isinstance(spec,dict):raise CircuitError('Expected behaviour specification is required.')
    if 'reference' in spec and spec['reference'] is not None:
        c=validate(spec['reference'])
        if c['qubits']!=n:raise CircuitError('Reference qubit count differs from tested circuit.')
        v=pure_state(c)
        if v is None:raise CircuitError('Reference must be a unitary state-preparation circuit.')
        return v
    key=spec.get('target','bell_phi_plus')
    v=state_zero(n)
    if key=='zero':return v
    if key.startswith('bell_'):
        if n!=2:raise CircuitError('Bell targets require exactly 2 qubits.')
        v[:]=0
        pair={'bell_phi_plus':(0,3,1),'bell_phi_minus':(0,3,-1),'bell_psi_plus':(1,2,1),'bell_psi_minus':(1,2,-1)}.get(key)
        if pair is None:raise CircuitError('Unknown Bell state target.')
        v[pair[0]]=1/np.sqrt(2);v[pair[1]]=pair[2]/np.sqrt(2);return v
    if key=='ghz':
        v[:]=0;v[0]=v[-1]=1/np.sqrt(2);return v
    if key=='uniform':return np.ones(2**n,complex)/np.sqrt(2**n)
    raise CircuitError('Unknown expected-state target.')

def inspect(raw,spec):
    c=validate(raw)
    target=state_for_spec(spec,c['qubits'])
    actual=pure_state(c)
    if actual is None:raise CircuitError('Debugging currently supports unitary circuits; remove measurement and reset gates first.')
    fid=fidelity(actual,target)
    diffs=[{'state':bitlabel(i,c['qubits']),'expected':round(float(abs(target[i])**2),6),'actual':round(float(abs(actual[i])**2),6)} for i in range(len(actual)) if abs(abs(target[i])**2-abs(actual[i])**2)>1e-5]
    hints=[]
    if fid>=1-1e-9:hints.append('State-preparation specification is satisfied (up to global phase).')
    else:
        hints.append('The state differs from the specified target; inspect gate orientation, placement and parameters.')
        if any(g['type'] in ('CZ','CX') for g in c['gates']):hints.append('Check controlled-gate type and control/target order.')
        if not any(g['type']=='H' for g in c['gates']):hints.append('No Hadamard gate found. Check whether superposition is required.')
        if diffs:hints.append('Measurement probabilities differ. See the state-by-state comparison below.')
        else:hints.append('Probabilities agree but relative phases differ; inspect phase gates and rotations.')
    # Fault location is a heuristic: rank single-change repairs, not a proof of a bad gate.
    return {'fidelity':round(fid,9),'passed':fid>=1-1e-9,'differences':diffs,'hints':hints,'expected':[{'state':bitlabel(i,c['qubits']),'probability':round(float(abs(x)**2),8)} for i,x in enumerate(target) if abs(x)>1e-9], 'actual':[{'state':bitlabel(i,c['qubits']),'probability':round(float(abs(x)**2),8)} for i,x in enumerate(actual) if abs(x)>1e-9], 'scope':'Unitary state-preparation from |0…0>; verifies the final state, not full unitary equivalence.'}

def unitary(c):
    c=validate(c)
    if c['qubits']>5:raise CircuitError('Full unitary verification is limited to 5 qubits.')
    if any(g['type'] in ('RESET','MEASURE') for g in c['gates']):raise CircuitError('Full-unitary verification requires circuits without measurements or resets.')
    columns=[]
    for i in range(2**c['qubits']):
        s=np.zeros(2**c['qubits'],complex);s[i]=1
        for g in c['gates']:
            if g['type']!='BARRIER':s=apply_matrix(s,g['targets'],matrix_for(g),c['qubits'])
        columns.append(s)
    return np.column_stack(columns)

def verify(raw,reference,mode='unitary'):
    a=validate(raw);b=validate(reference)
    if a['qubits']!=b['qubits']:raise CircuitError('Circuits have different qubit counts.')
    if mode=='state':
        p=pure_state(a);q=pure_state(b)
        if p is None or q is None:raise CircuitError('State verification requires unitary circuits.')
        score=fidelity(p,q)
        return {'equivalent':score>=1-1e-9,'score':round(score,10),'mode':'state','detail':'Checks only output from the all-zero initial state (up to global phase).'}
    A=unitary(a);B=unitary(b)
    dot=np.vdot(B,A);phi=dot/abs(dot) if abs(dot)>1e-12 else 1+0j
    delta=float(np.linalg.norm(A-phi*B,ord='fro'))
    equivalent=delta<1e-7
    return {'equivalent':equivalent,'score':round(max(0,1-delta/(2**(a['qubits']/2)*2)),10),'mode':'unitary','frobeniusDistance':round(delta,10),'detail':'Full unitary equivalence up to global phase.'}

INVERSES={'I':'I','H':'H','X':'X','Y':'Y','Z':'Z','CX':'CX','CY':'CY','CZ':'CZ','CH':'CH','SWAP':'SWAP','CCX':'CCX','CSWAP':'CSWAP','S':'SDG','SDG':'S','T':'TDG','TDG':'T'}

def optimize(raw):
    c=validate(raw);before=metrics(c)
    original=[dict(g) for g in c['gates']]
    gates=[dict(g) for g in original];actions=[]
    # Remove barriers and identity gates; barriers affect compilation boundaries, not unitary.
    gates=[g for g in gates if g['type']!='I']
    if len(gates)!=len(original):actions.append('Removed identity gates.')
    for _ in range(10):
        changed=False;i=0
        while i<len(gates)-1:
            a=gates[i];b=gates[i+1]
            if a['targets']==b['targets'] and a['type'] not in SPECIAL and b['type'] not in SPECIAL:
                same_inverse=INVERSES.get(a['type'])==b['type']
                rotation_cancel=a['type']==b['type'] and a['type'] in ('RX','RY','RZ','P','CP','CRX','CRY','CRZ','RZZ')
                if same_inverse:
                    actions.append(f'Removed adjacent {a["type"]} + {b["type"]} gates.');gates[i:i+2]=[];changed=True;continue
                if rotation_cancel:
                    total=a.get('angle',0)+b.get('angle',0)
                    # Controlled spin rotations have a 4π period; treating 2π as identity changes the controlled phase.
                    period = 4*math.pi if a['type'] in ('CRX','CRY','CRZ') else 2*math.pi
                    if abs((total+period/2)%period-period/2)<1e-8:
                        actions.append(f'Cancelled adjacent {a["type"]} rotations.');gates[i:i+2]=[]
                    else:
                        gates[i]={'type':a['type'],'targets':a['targets'],'angle':total};gates.pop(i+1);actions.append(f'Merged adjacent {a["type"]} rotations.')
                    changed=True;continue
            i+=1
        if not changed:break
    candidate={**c,'gates':gates}
    # Mathematically validate before returning any changed quantum program.
    if original!=gates:
        try:proof=verify(c,candidate,'unitary') if c['qubits']<=5 else verify(c,candidate,'state')
        except CircuitError:
            proof={'equivalent':False,'detail':'Could not verify changed circuit.'}
        if not proof['equivalent']:
            return {'circuit':c,'before':before,'after':before,'actions':['Transformation was rejected because verification did not pass.'],'verification':proof}
    else:proof={'equivalent':True,'mode':'identity','detail':'Circuit unchanged.'}
    return {'circuit':candidate,'before':before,'after':metrics(candidate),'actions':actions or ['No applicable safe local simplifications found.'],'verification':proof}

def repair(raw,spec,max_candidates=300):
    c=validate(raw);start=inspect(c,spec)
    if start['passed']:return {'original':start,'suggestions':[],'evaluated':0,'message':'Circuit already satisfies the specified target.'}
    if c['qubits']>5:raise CircuitError('Automatic repair currently supports up to 5 qubits.')
    max_candidates=max(1,min(int(max_candidates),1200))
    original=c['gates'];candidates=[]
    replacement_map={1:['H','X','Y','Z','S','SDG','T','TDG','RX','RY','RZ'],2:['CX','CY','CZ','CH','SWAP','CP'],3:['CCX','CSWAP']}
    for i,g in enumerate(original):
        if g['type'] in SPECIAL:continue
        arity=len(g['targets'])
        for kind in replacement_map.get(arity,[]):
            if kind==g['type']:continue
            replacement={'type':kind,'targets':g['targets'].copy()}
            if kind in PARAMETRIC:replacement['angle']=g.get('angle',math.pi)
            new=original.copy();new[i]=replacement
            candidates.append((f'Replace gate {i+1} ({g["type"]}) with {kind}',new,i))
        if len(g['targets'])>=2:
            ng={**g,'targets':list(reversed(g['targets']))}
            new=original.copy();new[i]=ng
            candidates.append((f'Reverse qubit order at gate {i+1}',new,i))
        new=original[:i]+original[i+1:]
        candidates.append((f'Remove gate {i+1} ({g["type"]})',new,i))
    # Limited insertion support: one well-defined repair operation; search remains bounded.
    for i in range(len(original)+1):
        for q in range(c['qubits']):
            for kind in ('H','X','Z'):
                new=original[:i]+[{'type':kind,'targets':[q]}]+original[i:]
                candidates.append((f'Insert {kind} on q{q} before gate {i+1}',new,i))
    target=state_for_spec(spec,c['qubits']);results=[];evaluated=0
    for desc,gates,idx in candidates[:max_candidates]:
        candidate={**c,'gates':gates}
        s=pure_state(candidate)
        if s is None:continue
        score=fidelity(s,target);evaluated+=1
        if score>start['fidelity']+1e-7:
            results.append({'description':desc,'fidelity':round(score,9),'passed':score>=1-1e-9,'changedIndex':idx,'circuit':candidate,'edits':1})
    results.sort(key=lambda x:(not x['passed'],-x['fidelity'],x['edits'],x['changedIndex']))
    return {'original':start,'suggestions':results[:8],'evaluated':evaluated,'message':'Single-edit candidate search. A correction is confirmed only against the stated state-preparation target.'}

def benchmark(raw,shots=512):
    c=validate(raw);optimized=optimize(c);initial=simulate(c,shots,seed=7);final=simulate(optimized['circuit'],shots,seed=7)
    return {'before':initial['metrics'],'after':final['metrics'],'verification':optimized['verification'],'actions':optimized['actions'],'originalCounts':initial['counts'],'optimizedCounts':final['counts'],'improvement':{'gates':initial['metrics']['gates']-final['metrics']['gates'],'depth':initial['metrics']['depth']-final['metrics']['depth'],'twoQubitGates':initial['metrics']['twoQubitGates']-final['metrics']['twoQubitGates']}}

ALIAS={'cnot':'CX','toffoli':'CCX'}
def parse_angle(source):
    source=source.strip().replace('π','pi')
    if len(source)>120:raise CircuitError('Angle expression is too long.')
    tree=ast.parse(source,mode='eval')
    def visit(node):
        if isinstance(node,ast.Expression):return visit(node.body)
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):return float(node.value)
        if isinstance(node,ast.Name) and node.id=='pi':return math.pi
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):return -visit(node.operand) if isinstance(node.op,ast.USub) else visit(node.operand)
        if isinstance(node,ast.BinOp) and isinstance(node.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            a,b=visit(node.left),visit(node.right)
            return a+b if isinstance(node.op,ast.Add) else a-b if isinstance(node.op,ast.Sub) else a*b if isinstance(node.op,ast.Mult) else a/b
        raise CircuitError('Unsupported gate angle expression.')
    result=visit(tree)
    if not math.isfinite(result):raise CircuitError('Invalid gate angle.')
    return result

def from_qasm(source):
    if not isinstance(source,str) or len(source)>40000:raise CircuitError('QASM source must be under 40 KB.')
    source=re.sub(r'//[^\n]*','',source)
    source=source.replace('\n',' ')
    tokens=[x.strip() for x in source.split(';') if x.strip()]
    n=None;gates=[]
    for line in tokens:
        if re.fullmatch(r'OPENQASM\s+2\.0',line,re.I) or re.fullmatch(r'include\s+"qelib1\.inc"',line,re.I):continue
        m=re.fullmatch(r'qreg\s+q\[(\d+)\]',line,re.I)
        if m:n=int(m.group(1));continue
        if re.fullmatch(r'creg\s+c\[\d+\]',line,re.I):continue
        m=re.fullmatch(r'measure\s+q\[(\d+)\]\s*->\s*c\[\d+\]',line,re.I)
        if m:gates.append({'type':'MEASURE','targets':[int(m.group(1))]});continue
        m=re.fullmatch(r'reset\s+q\[(\d+)\]',line,re.I)
        if m:gates.append({'type':'RESET','targets':[int(m.group(1))]});continue
        m=re.fullmatch(r'barrier\s+(.+)',line,re.I)
        if m:
            targets=[int(x) for x in re.findall(r'q\[(\d+)\]',m.group(1))]
            gates.append({'type':'BARRIER','targets':targets});continue
        m=re.fullmatch(r'([a-zA-Z][a-zA-Z0-9_]*)(?:\(([^()]*)\))?\s+(.+)',line)
        if not m:raise CircuitError(f'Unsupported QASM statement: {line[:80]}')
        kind=ALIAS.get(m.group(1).lower(),m.group(1).upper())
        targets=re.findall(r'q\[(\d+)\]',m.group(3))
        if not targets or re.sub(r'q\[\d+\]|[\s,]','',m.group(3)):
            raise CircuitError(f'Unsupported qubit arguments: {line[:80]}')
        gate={'type':kind,'targets':[int(t) for t in targets]}
        if m.group(2) is not None:gate['angle']=parse_angle(m.group(2))
        gates.append(gate)
    if n is None:raise CircuitError('QASM must declare qreg q[n].')
    return validate({'name':'Imported QASM','qubits':n,'gates':gates})

def to_qasm(raw):
    c=validate(raw)
    lines=['OPENQASM 2.0;','include "qelib1.inc";',f'qreg q[{c["qubits"]}];',f'creg c[{c["qubits"]}];']
    for g in c['gates']:
        name=g['type'].lower();args=','.join(f'q[{q}]' for q in g['targets'])
        if name=='measure':lines.append(f'measure {args} -> c[{g["targets"][0]}];')
        elif name=='barrier':lines.append(f'barrier {args if args else "q"};')
        elif name=='reset':lines.append(f'reset {args};')
        else:
            param=f'({g["angle"]:.12g})' if g['type'] in PARAMETRIC else ''
            lines.append(f'{name}{param} {args};')
    return '\n'.join(lines)+'\n'

def to_qiskit(raw):
    c=validate(raw)
    lines=['from qiskit import QuantumCircuit','from qiskit_aer import AerSimulator','',f'qc = QuantumCircuit({c["qubits"]}, {c["qubits"]})']
    for g in c['gates']:
        t=g['type'];args=', '.join(str(q) for q in g['targets'])
        if t=='MEASURE':lines.append(f'qc.measure({args}, {args})')
        elif t=='BARRIER':lines.append(f'qc.barrier({args})' if args else 'qc.barrier()')
        elif t=='RESET':lines.append(f'qc.reset({args})')
        elif t in PARAMETRIC:lines.append(f'qc.{t.lower()}({g["angle"]:.12g}, {args})')
        else:lines.append(f'qc.{t.lower()}({args})')
    if not any(g['type']=='MEASURE' for g in c['gates']):lines.append('qc.measure_all()')
    lines+=['','sim = AerSimulator()','result = sim.run(qc, shots=1024).result()','print(result.get_counts())']
    return '\n'.join(lines)+'\n'

def trace_states(raw):
    """Stepwise unitary state inspection for small circuits (including initial |0…0>)."""
    c=validate(raw)
    if len(c['gates'])>80:raise CircuitError('Stepwise inspection is limited to 80 gates.')
    if any(g['type'] in ('MEASURE','RESET') for g in c['gates']):
        raise CircuitError('Stepwise pure-state inspection does not support measurement or reset. Use sampled simulation instead.')
    s=state_zero(c['qubits'])
    def snapshot(i,g):
        return {'step':i,'gate':g,'probabilities':[{'state':bitlabel(j,c['qubits']),'probability':round(float(abs(x)**2),8)} for j,x in enumerate(s) if abs(x)>1e-8], 'bloch':[bloch(s,k,c['qubits']) for k in range(c['qubits'])]}
    out=[snapshot(0,{'type':'INITIAL','targets':[]})]
    for i,gate in enumerate(c['gates']):
        if gate['type']!='BARRIER':s=apply_matrix(s,gate['targets'],matrix_for(gate),c['qubits'])
        out.append(snapshot(i+1,gate))
    return {'circuit':c,'steps':out,'total':len(out)}
