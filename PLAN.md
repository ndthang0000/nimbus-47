# Coding Test Implementation Plan

Status: ingestion, API upload, retrieval, delta sync and Docker are verified. Manual DigitalOcean execution succeeded and daily cron is installed/active. A captioned evidence video, UI screenshot, cloud artifacts and submission notes are packaged. Scheduled-trigger execution is verified; saved UI prompt persistence remains unverified. Part 2 Planning remains separate.

Scope: Part 1 Coding. Part 2 Planning is a separate deliverable. Budget: approximately eight focused hours, within the three-day submission window measured from the invitation email.

## Objective

Help Center → Python → Markdown → API knowledge-base upload → grounded assistant answers with source URLs.
Deploy a daily cloud job that uploads only new or changed content. Use the platform UI for the required demo; a custom chat frontend is outside the required scope.

## Implementation Steps

| Step | Budget | Work | Acceptance criteria |
|---|---:|---|---|
| 1. Explore and select a provider | 30 min | Try OptiBot; verify current APIs, billing and UI capabilities | Product observations and provider decision recorded |
| 2. Python setup | 30 min | Entrypoint, dependencies, environment template and validation | Configuration validation succeeds without logging secrets |
| 3. Article ingestion | 90 min | Paginated Zendesk API; 50 English articles including YouTube; HTML conversion | Unique Markdown files with title/source, preserved headings, code and relative links |
| 4. Knowledge base and assistant | 90 min | Exact prompt, Python API upload, indexing polling and File Search | Successful retrieval, honest file/chunk counts, UI screenshot with citations |
| 5. Delta synchronization | 60 min | Article IDs, normalized hashes, remote IDs and replacement of stale content | Added/updated/skipped counts; unchanged runs do not upload |
| 6. Docker and daily cloud job | 60 min | Single-run container, daily schedule and durable state | Successful cloud execution, daily schedule and accessible logs |
| 7. Verification | 45 min | In-scope and out-of-scope questions; failure and retry scenarios | Valid source citations; failed indexing never marked successful |
| 8. Submission | 75 min | One-page README, video, secret review and clear commits | Separate Part 1 links ready to submit together with Part 2 |

Total: 480 minutes. Record actual time. If the budget is exhausted, submit working functionality and explain what was cut.

## Technical Decisions

- OpenAI is selected. Use Responses API and File Search because Assistants API was retired. Confirm the equivalent UI demo with HR if needed.
- Python handles ingestion and API uploads. Dependencies are declared in requirements.txt.
- The dataset contains 50 articles, including the YouTube guide; remaining articles are selected alphabetically. This does not guarantee full product coverage.
- Every document and prepared chunk contains an `Article URL:` source line.
- Local chunks are at most 3000 cl100k tokens, with repeated title/source and no overlap. Provider chunking uses 4096 tokens and zero overlap.
- Distinguish source article counts, prepared chunks and completed indexed files. The provider does not expose a direct internal embedding chunk total.
- Persist remote upload IDs immediately for recovery; mark indexing successful only after completion. Delta replacement will remove stale retrieval content.
- Cloud state must survive ephemeral containers: choose persistent storage or object storage.
- Use a fixed daily schedule, prevent overlapping runs and configure cloud secrets outside Git. UTC timestamps are the deployment target; current CLI logging uses host time.

## Planned Layout

```text
main.py
src/                 # config, scraper, Markdown conversion, provider; sync pending
tests/              # focused behavioral checks
data/articles/      # generated Markdown and scrape report (ignored)
state/              # upload IDs and reports (ignored; durable storage needed on cloud)
artifacts/          # reviewed screenshots and submission evidence
Dockerfile           # pending
.dockerignore        # pending
.env.sample
requirements.txt
README.md
PLAN.md
```

## Required Prompt

You are OptiBot, the customer-support bot for OptiSigns.com. • Tone: helpful, factual, concise. • Only answer using the uploaded docs. • Max 5 bullet points; else link to the doc. • Cite up to 3 "Article URL:" lines per reply.

## Verification Scenarios

- Conversion preserves headings, fenced code and relative links while removing irrelevant markup.
- Pagination filters drafts/non-English content and deduplicates article IDs.
- Empty, unchanged and updated manifests produce correct added/skipped/updated counts.
- Failed uploads/indexing are recoverable and never recorded as successful.
- A configured container runs once and exits zero; configuration or pipeline failures exit nonzero.
- Daily runs retain remote IDs and avoid duplicate or stale documents.
- In-scope answers cite uploaded sources; unsupported questions do not produce invented instructions.

## Submission Checklist

- [x] At least 30 clean Markdown articles with source URLs (50 collected).
- [x] Python API upload, indexing verification and explicit count definitions.
- [ ] Exact prompt configured in the UI; YouTube answer screenshot with citations.
- [x] Dockerfile and daily cloud job with delta synchronization (manual cloud execution verified).
- [x] Job logs and last-run artifact packaged in the repository.
- [x] Environment template and secret exclusions.
- [x] GitHub repository with a non-brand name and clear commits.
- [x] Concise README, screenshot and captioned evidence video packaged.
- [ ] Part 1 and Part 2 separately labeled and submitted together.

## User-Owned Setup

AI credentials stay in local environment configuration, never in chat or Git. Cloud and GitHub accounts are needed for deployment and publishing. API usage is billable; cloud deployment has not been created yet.
