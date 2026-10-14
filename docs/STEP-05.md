# Step 5: Delta Synchronization

## Run

```powershell
.\.venv\Scripts\python.exe main.py --sync
```

This re-fetches the configured English dataset, converts it to Markdown and synchronizes it with the existing vector store. `--upload-only` applies the same delta logic to the existing local scrape report without fetching Zendesk again. Neither command asks the language model.

## Decisions

- Article IDs identify documents even when titles and filenames change.
- SHA-256 hashes cover normalized Markdown, including title and source URL; timestamp-only changes do not trigger uploads.
- New articles are added. Matching hashes are skipped. Changed articles upload a complete replacement Markdown file.
- The replacement file must finish indexing before the old file is detached from the vector store.
- Stable article IDs prevent filename changes from creating a second logical article.
- Articles absent from the selected 50 are retained. Selection changes are not evidence of source deletion; deletion reconciliation is outside this step.
- State carries schema_version=2 and ingestion_strategy=whole_article_v1. Mismatched state is rejected; identical hashes skip only under the same ingestion strategy.

## Recovery and State

`state/openai.json` contains active articles and pending replacement transactions. Each uploaded remote ID is persisted. Indexing failure retains the old article and permits another batch attempt using the uploaded IDs. Indexing timeout resumes the saved batch. Detachment failure resumes cleanup without uploading replacement files again. Missing old attachments are treated as already detached.

An OS file lock serializes vector-store synchronization for processes sharing the same state directory. The lock releases when the process exits or crashes. The scraper output directory must also be used by one scheduled job at a time; cloud scheduling must prevent overlapping jobs or use isolated scrape output directories.

The swap is not atomic on the remote service: both versions may briefly coexist, and search removal can be eventually consistent. The CLI blocks questions while a transaction is pending. Direct Playground queries are not blocked. Detached files remain in the Files API; permanent raw-file cleanup is deliberately separate.

An abrupt crash after the API accepts a create request but before its ID is persisted can leave an orphan remote object. Persisted transactions recover ordinary upload/indexing/cleanup failures, but do not guarantee exactly-once remote creation across that narrow window.

## Logs and Reports

Counts represent source articles:

```text
Sync complete: added=0 updated=0 skipped=50 uploaded_files=0
```

`state/sync-report.json` records the completion timestamp, article counts, actual file uploads, active indexed files, provider counts and storage bytes. `state/upload-report.json` is updated with the same report. Failed runs exit nonzero and leave pending state; the last successful report remains intact.

## Verification

- Live re-scrape: 50 articles skipped, no uploads, original store retained.
- Mocked new article: added once; unchanged rerun performs no upload/indexing.
- Mocked renamed/shrunk article: one full replacement file, old attachment removed after indexing.
- Failed indexing: old active hash retained; retry reuses uploaded files.
- Failed cleanup: retry resumes deletion without re-uploading or re-indexing.
- Selection omission: previous articles retained.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Docker, durable cloud storage and daily scheduling are step 6.
