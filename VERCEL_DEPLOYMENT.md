# Qubitrail V4.1 — Vercel runtime deployment fix

This revision addresses multiple possible causes of `500 FUNCTION_INVOCATION_FAILED`. It is not possible to identify the precise production exception without Vercel's *Runtime Logs*.

## Changes
- `app.py`: standard FastAPI entrypoint at the repository root.
- `pyproject.toml`: declares Vercel entrypoint **and Python runtime dependencies**. Pins Python 3.12 for consistency.
- `public/index.html` and `public/assets/`: frontend copies so Vercel can serve static files through its CDN. `frontend/` is retained for local use.
- `backend/main.py`: tolerates database initialization failure during import; uses fallback frontend location where available; reports a clear 503 if frontend files are missing.
- `backend/store.py`: retains the previous fix that uses writable `/tmp/qubitrail` on Vercel. **This is ephemeral and not reliable persistence.**

## Upload through GitHub
1. Place **the contents of the `Qubitrail` directory** at your Vercel project root (where `app.py`, `pyproject.toml`, `requirements.txt`, `frontend/`, `backend/`, and `public/` coexist).
2. Commit and push these files. From the project root: `git add . && git commit -m "Fix Vercel runtime bootstrap" && git push`.
3. In Vercel project settings: Framework Preset = `FastAPI`; Root Directory = repository directory holding `app.py` (usually `./`); leave Build Command and Output Directory unset.
4. Redeploy the latest commit. Visit `/api/health` and then `/`.

## If there is still a 500 error
1. Vercel dashboard > Qubitrail > **Logs** (not Build Logs).
2. Filter status 500 and click the failed `/` or `/api/health` request.
3. Copy the **Python traceback / error lines**, especially the final exception line.
4. Typical meanings:
   - `ModuleNotFoundError: No module named 'numpy'`: Python dependencies missing from runtime installation.
   - `FileNotFoundError` for `frontend`: frontend directory missing from function bundle.
   - `sqlite3.OperationalError: unable to open database file`: SQLite path or directory is not writable.
   - `ModuleNotFoundError: backend`: wrong root directory or source not pushed.

## Limitations
- SQLite in `/tmp` is **not persistent** across Vercel instances, deployments, or cold starts. Project saving is only for transient demonstration; use a hosted database for durable projects.
- There is no user authentication. Do not store confidential projects or personal information on a publicly accessible deployment.
- Heavy quantum simulation or automatic repair requests may hit serverless resource/time limits; this patch does not alter algorithm complexity.
- The optional Qiskit Aer dependency is not installed on Vercel. The included NumPy engine works without it.
