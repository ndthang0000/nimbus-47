# Nimbus 47

A Python support assistant pipeline: collect 50 English OptiSigns articles, convert them to Markdown, upload through the OpenAI API, and synchronize changes daily.

## Setup

Requires **Python 3.14** and an **OpenAI API key with billing enabled**. Clone this repository and open its root directory.

**Windows (PowerShell)**

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.sample .env }
```

**macOS / Linux (bash or zsh)**

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
[ -f .env ] || cp .env.sample .env
```

In `.env`, set `AI_PROVIDER=openai`, `API_KEY=<your-key>` and `ARTICLE_LIMIT=50`. Keep credentials private. No virtual-environment activation is needed.

## Run Locally

**Windows:**

```powershell
.\.venv\Scripts\python.exe main.py --sync
.\.venv\Scripts\python.exe main.py --ask "How do I add a YouTube video?"
```

**macOS / Linux:**

```bash
.venv/bin/python main.py --sync
.venv/bin/python main.py --ask "How do I add a YouTube video?"
```

`--sync` fetches articles, saves Markdown in `data/articles/`, uploads new/changed articles, and waits for indexing. It saves progress in `state/`; keep this directory between runs. Optional commands: `--check-config`, `--scrape-only`, `--upload-only`. API usage may incur charges.

**Chunking:** each article is uploaded whole. OpenAI performs chunking and embedding using static **4096-token chunks, zero overlap**. The dataset has 50 indexed files; internal embedding chunk totals are not exposed.

## Daily Job Logs

Docker runs the pipeline on DigitalOcean daily at **19:00 UTC / 02:00 Vietnam time**. Article IDs and SHA-256 determine `added`, `updated` and `skipped`; unchanged articles are not uploaded.

[Execution log](https://github.com/ndthang0000/nimbus-47/blob/main/artifacts/cloud-verification.txt) | [Last-run artifact](https://github.com/ndthang0000/nimbus-47/blob/main/artifacts/digitalocean-last-run.json) | [Cron trigger evidence](artifacts/cron-trigger.txt)

The current image passed a manual cloud run: **50 skipped, zero uploads, exit 0**. Cron-trigger evidence records the earlier scheduled execution. These links are captured evidence, not live dashboards. [Docker and deployment instructions](docs/STEP-06.md).

## Assistant Screenshot

Sample question: **How do I add a YouTube video?** The Playground answer shows File Search retrieval and a source citation.

<a href="artifacts/assistant-playground.png"><img src="artifacts/assistant-playground.png" alt="Assistant answering the YouTube sample question with a cited source" width="480"></a>

The screenshot predates the current store; replace it with a capture using **Nimbus 47 Articles** before submission. [Implementation limitations](docs/SUBMISSION.md).
