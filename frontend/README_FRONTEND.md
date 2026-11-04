# Qubitrail V4 — Meridian frontend

This is a complete replacement for Qubitrail V3's interface, built as a product-grade interactive quantum studio. **No Node/npm or frontend build step is required.** HTML, CSS and modern vanilla JavaScript are served by FastAPI.

## Changes from V3

- Added an immersive Discover product entry screen with a quantum-state visual, useful product journeys, and recent projects.
- Removed left navigation rail and left gate shelf. Replaced them with application-wide workspace navigation and a categorized horizontal gate dock, directly beneath the main quantum canvas.
- Entirely new dark-purple design system, product typography, iconography, wire diagrams, code console, contextual inspector, and responsive layout.
- Circuit design is given the majority of the available screen. Gate dragging, placement, selection, qubit editing, and undo/redo still use the actual original backend data model.
- Rebuilt dedicated interfaces for **Repair**, **Observe**, **Optimize**, and **Noise** with circuit previews, simulation visualizations, verification, and contextual controls rather than generic dashboard cards.
- Retained Library, Project Vault, benchmarks, deterministic Quantum Guide, QASM import/export, Python code export, project history, keyboard shortcuts, dark/light themes and local browser drafts.

## How to install the frontend-only release

Stop Qubitrail, back up your current `frontend` folder, then replace the contents of that folder with `app.js`, `styles.css`, `index.html`, and `favicon.svg` from this package. Do **not** delete your `data` directory. Run `python run.py` again.

## Testing

`python -m pytest -q` — backend regression tests.

`node tests/frontend_smoke.js` — structural frontend tests (only with the full project package).

The suite also passed Chromium interaction checks using an in-process FastAPI test-client bridge for browser API calls.

## Technical boundaries

Automatic repair is bounded, specification-driven, and supports small circuits; it is not universal arbitrary quantum repair. The quantum guide is deterministic offline content rather than an external generative AI. Optional quantum hardware and shared cloud collaboration are not part of this release. External fonts enhance the UI where internet access permits; system font fallbacks keep it functional offline.
