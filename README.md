# Nimbus 47

Python support-document ingestion with OpenAI File Search and a daily Docker job.

## Setup and Run

Python 3.14. Create a virtual environment, install requirements.txt, copy .env.sample to .env and set AI_PROVIDER=openai and API_KEY. Never commit credentials.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --check-config
.\.venv\Scripts\python.exe main.py --scrape-only
.\.venv\Scripts\python.exe main.py --upload-only
.\.venv\Scripts\python.exe main.py --ask "How do I add a YouTube video?"
.\.venv\Scripts\python.exe main.py --sync
```

## Design

Paginated Zendesk API collects 50 English articles including YouTube. Markdown preserves headings, code and relative links with canonical source URLs. Python uploads through the API, polls indexing and persists remote IDs. Responses API replaces the retired Assistants API; the required prompt is unchanged.

Chunking: <=3000 cl100k tokens per Markdown part, preferably paragraph boundaries, repeated title/source, no overlap. Provider static chunking: 4096/0. Verified: 50 articles, 55 indexed files, 340,908 storage bytes. Prepared chunks and indexed files are reported separately; internal embedding chunk totals are not exposed.

Sync uses article IDs and SHA-256 of normalized Markdown. Replacement indexing finishes before old attachments are removed. Journaled transactions resume after failures; host locking prevents overlapping jobs. Omitted articles and detached raw files are retained. See [recovery limits](docs/STEP-05.md).

## Docker and Cloud

Build: `docker build -t nimbus-47:latest .`. Supply runtime secrets and mount state/data at /state and /data. Container runs sync once and exits. See [deployment commands](docs/STEP-06.md), including Windows path overrides.

DigitalOcean manual execution succeeded. Cron is installed for **19:00 UTC / 02:00 Vietnam daily**, service active; an actual scheduled invocation has not yet been observed. State survives container replacement. Store expires after seven inactive days.

## Evidence

- [Cloud artifact](artifacts/digitalocean-last-run.json), [execution log](artifacts/cloud-verification.txt), [schedule](artifacts/cloud-schedule.txt).
- [Playground screenshot](artifacts/assistant-playground.png), [video walkthrough](artifacts/coding-demo.mp4).
- [12 passing tests](artifacts/test-results.txt): `python -m unittest discover -s tests -v`.

UI uses GPT-6 Luna; CLI uses GPT-5.4 Mini. UI answer is correct and cited, but uses numbered steps rather than bullets; the Article URL label is present. Screenshot shows a draft prompt; saved UI configuration remains unverified. Video is a captioned evidence walkthrough, not a continuous screen recording. See [submission notes](docs/SUBMISSION.md).
