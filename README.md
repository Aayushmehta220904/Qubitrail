# Qubitrail V4 — Meridian Quantum Studio

**Trace. Repair. Verify.**

Qubitrail is a software-only quantum circuit development environment. **V4 rebuilds the complete UI into a refined product application:** top-level workspaces, a spacious interactive circuit canvas, a categorized gate dock, contextual state inspector, and dedicated analysis environments for simulation, automatic repair, optimization and noise. The established FastAPI/NumPy quantum engine and SQLite project schema remain compatible.

**No quantum computer, API key, Node.js, paid cloud services or separate frontend build step is required.**

## Start Qubitrail

Requirements: Python 3.10+, a modern browser.

**Windows:**

```powershell
cd Qubitrail
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python run.py
```

**macOS / Linux:**

```bash
cd Qubitrail
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Then open **http://127.0.0.1:8000**. Or run `start.bat` on Windows / `bash start.sh` on macOS or Linux.

If the default port is unavailable, run `uvicorn backend.main:app --host 127.0.0.1 --port 8010` and open `http://127.0.0.1:8010`.

## What's redesigned in V4?

- **Product launch experience:** a dedicated Discover home screen with an immersive quantum-state illustration, featured entry paths into Studio, Repair and Observe, and recent saved projects.
- **Product architecture:** no dashboard navigation rail or left gate shelf. A consistent application bar and full-width workspace navigation keep content central.
- **Quantum Studio:** large dark interactive circuit canvas with luminous gates, drag-and-drop placement, categorized bottom gate library, quick editing, undo/redo and focused mode.
- **Contextual inspector:** live simulation probabilities, quantum-state visual, gate properties and direct analysis actions.
- **Dedicated Repair Laboratory:** circuit under test, target/reference specification, fidelity gauge, diagnostic workflow, candidate modifications and verified repair actions.
- **Dedicated Observe, Optimize and Noise workspaces:** interactive charts, experiment controls, statevector data, transformation metrics and noise comparisons.
- **Project Library / Vault / Research / Guide:** retained and restyled as integrated workspaces.
- **Usability:** keyboard shortcuts, project history, JSON-free import/export workflows, command palette, responsive interface, light/dark themes, and local draft recovery.

### Workflows

**Try the signature repair:** Design → **Load repair demo** → **Repair** → **Find a repair** → inspect candidates → **Apply fix**. This loads a Bell-state circuit with `CZ` where `CX` should be, then finds an improved single-edit correction against the specified target.

**Try quantum simulation:** Open **Design**, click **Run circuit**, then view results in the bottom terminal panel or the **Observe** workspace. Source code is available in **Source** (QASM 2 / Qiskit Python). The **Timeline** tab offers stepwise pure-state inspection.

**Try optimization:** Open **Library**, load *Redundant Gates — Optimize Me*, visit **Optimize**, run **Optimize circuit**, inspect the proof, then **Use optimized circuit**.

**Try noise:** Open **Noise Lab**, choose error rates, and run a noisy experiment. The comparative distribution shows baseline and noisy measurements.

**Try project saving:** Edit your circuit and click **Save**. If this is a new circuit, provide a project name. Later saves create snapshots; find and restore them in **Projects → History**.

### Shortcuts

| Shortcut | Action |
|---|---|
| Ctrl/⌘ + Enter | Run simulation |
| Ctrl/⌘ + S | Save project |
| Ctrl/⌘ + K | Command palette |
| Ctrl/⌘ + Z | Undo |
| Ctrl/⌘ + Shift + Z | Redo |
| Delete / Backspace | Remove selected gate |
| Escape | Close dialog |

## Actual technical scope

| Module | Implementation |
|---|---|
| Circuit editor | 1–8 qubits, native SVG, operations with validated target/angle inputs |
| Statevector simulation | NumPy quantum state evolution and measurement sampling |
| Circuit repair | Bounded single-edit candidate search; requires reference or target; up to 5 qubits |
| Circuit debugging | Expected-state comparison, fidelity, test differences and hints |
| Optimization | Local gate cancellation / rotation merging; transformations verified |
| Equivalence | Full-unitary check up to 5 qubits (global-phase aware); state-only comparison for larger circuits |
| Noise | Stochastic depolarizing, bit-flip, phase-flip, amplitude-damping and readout models |
| Stepwise tracing | Unit-only circuit state snapshots up to 80 operations |
| Import/export | Supported OpenQASM 2 subset and Qiskit Python source generation |
| Templates | 16 quantum circuits, including Bell, GHZ, Grover, Deutsch and QFT |
| Research | Optimizer benchmark and fixed six-case injected-fault repair suite |
| Storage | Local SQLite projects, snapshots and experiment history |
| Quantum Guide | Offline deterministic, rule-based content; not a generative LLM |
| Optional Qiskit Aer | Supported by separate optional dependencies; not needed for the UI |

**Limitations:** This is an educational/research prototype, not a universal quantum compiler, multi-edit repair system, validated physics error model, or real quantum hardware client. Noise and all numerical outputs are from the local simulator. No claim of general quantum advantage is made. Generative AI, accounts, live IBM hardware execution, and multiplayer collaboration are **not** included in the current functioning release.

## Testing

From the `Qubitrail` folder:

```bash
python -m pytest -q
node --check frontend/app.js          # optional: needs Node
node tests/frontend_smoke.js          # optional: needs Node
```

The 32 Python tests cover numerical quantum operations, verification, fault repair, QASM, noise and API persistence. The new Node smoke test checks 18 major UI render paths. The interface was also visually rendered and interaction-tested in headless Chromium, with browser `fetch` requests bridged directly to FastAPI's `TestClient` because direct browser navigation was restricted in the build environment. Those bridge tests exercised drag/drop, project saving, repairs, imports, simulation, optimization, noise, research and Guide.

## Architecture

```text
frontend/index.html    Minimal HTML entry point
frontend/styles.css    Complete V4 visual architecture
frontend/app.js        V4 circuit UI, workspaces and REST actions
backend/main.py        FastAPI application (unchanged in V4)
backend/quantum.py     NumPy simulator, verifier, optimizer, repair
backend/library.py     16 quantum templates
backend/research.py    Repair benchmark
backend/guide.py       Offline quantum guide
backend/store.py       SQLite projects, history and experiments
run.py                 Local launcher
```

API docs after starting server: **http://127.0.0.1:8000/api/docs**.

**Updating from V2 or V3:** The safest path is to replace only the old `frontend/` directory with the new `frontend/` files. Do not delete your existing `data/` directory. The full-project ZIP contains the same backend files as V2 but deliberately does not package an example database.


## Deploy to Vercel

See [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md) for platform fixes and important persistence/security warnings.
