# Nimbus 47

Python knowledge ingestion and daily synchronization coding exercise.

Status: ingestion, API upload, File Search and delta synchronization verified. Docker/deployment files prepared; cloud execution, screenshot packaging and artifact publication remain pending.
See [PLAN.md](PLAN.md) for the eight-hour implementation plan and acceptance criteria.

Local setup: `py -m venv .venv`, then `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
Copy `.env.sample` to `.env` if absent, then set provider and API key (never commit secrets).
Validate: `.venv\Scripts\python.exe main.py --check-config`.
Scrape: `.venv\Scripts\python.exe main.py --scrape-only` (no AI API calls).
Output: `data/articles/`, including `scrape-report.json` and YouTube guidance.
Checks: `.venv\Scripts\python.exe -m unittest discover -s tests -v`.
See `docs/STEP-03.md` for pagination and conversion behavior.

Upload/index: `.venv\Scripts\python.exe main.py --upload-only`.
Demo: `.venv\Scripts\python.exe main.py --ask "How do I add a YouTube video?"`.
Uses Responses API because Assistants API was sunset; the instructions match the brief verbatim.
Chunking: <=3000 cl100k tokens per Markdown part, repeated title/source, paragraph boundaries where possible, no overlap;
provider static chunking 4096/0. Counts distinguish source articles, local chunks and completed indexed files;
the provider does not expose a direct internal embedding chunk total.
Verified: 50 articles → 55 chunk files, indexing completed (0 failed), 340,908 bytes stored.
The YouTube demo returned five bullets and the correct source Article URL.
State/report/demo output: `state/openai.json`, `state/upload-report.json`, `state/last-answer.md` (ignored by Git).
Daily-run entrypoint: `.venv\Scripts\python.exe main.py --sync` re-scrapes and logs added/updated/skipped.
Changed articles are indexed before old parts are detached; pending transactions resume after failures.
Verified live unchanged run: added=0 updated=0 skipped=50 uploaded_chunks=0. See `docs/STEP-05.md` for recovery limits.
UI screenshot packaging: pending; see `docs/STEP-04.md`. Cloud daily job/log link: pending.
Docker: `docker build -t nimbus-47:latest .`; pass credentials with `--env-file` and mount `/state` and `/data`.
Default container command runs sync once. DigitalOcean runner, daily cron and evidence instructions: `docs/STEP-06.md`.
