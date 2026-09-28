# Agentic RFP Evaluation and Supplier Ranking

A classroom mini project that evaluates multiple fictional supplier proposals with an evidence-grounded Evaluation Agent, validates its structured output, calculates transparent peer metrics in deterministic Python, persists the complete batch in SQLite, and presents the results in Streamlit.

## Business problem

Procurement teams need to compare lengthy proposals consistently. This application reduces repetitive reading and makes the comparison auditable: every criterion score has a justification and proposal evidence, while all arithmetic and tie-break decisions are computed by ordinary Python code.

The supplied PDFs are synthetic teaching examples. They do not represent real suppliers or confidential data.

## Architecture

```text
Streamlit UI
  └── Orchestrator Agent
       ├── Document Tool (PyMuPDF text extraction)
       ├── Evaluation Agent (OpenAI-compatible JSON model or deterministic DEMO)
       ├── Validation Tool (Pydantic contract + normalization + warnings)
       ├── Ranking Tool (pure deterministic Python)
       └── SQLite persistence (criteria, run snapshot, complete supplier JSON)
```

The run reloads the active criteria from SQLite and snapshots them against a generated `RFP_RUN_ID`. Each proposal then passes through PDF extraction, evaluation, schema validation and normalization. After all proposals are validated, Python calculates scorecards, peer benchmarks, PPI, and the final stable order. SQLite stores the full ranked supplier objects; Streamlit renders the leaderboard, evidence, risks, warnings, run details, and JSON export.

### Agent and tool responsibilities

- **Orchestrator Agent** controls the sequence and records run status.
- **Document Tool** only extracts selectable PDF text. It reports empty, corrupt, and image-only PDFs clearly; OCR is not included.
- **Evaluation Agent** scores proposal content against criteria loaded dynamically from SQLite. When configured, it calls an OpenAI-compatible Chat Completions endpoint with JSON mode. With no API key it uses a deterministic synthetic-profile evaluator, visibly labeled DEMO.
- **Validation Tool** runs Pydantic schema validation, safely parses JSON fences or an embedded JSON object, checks every active criterion, restores missing criteria with a zero score, clips scores, uses the database max score, preserves absent-evidence notices, and retains warnings in the export.
- **Ranking Tool** and `utils/scoring.py` contain no LLM calls. They perform every business calculation and sort.

## Project structure

```text
app.py
agents/                 # orchestrator and Evaluation Agent
database/               # schema, seed, SQLite operations
models/                 # Pydantic response contracts
prompts/                # dynamic evidence-grounded prompt
tools/                  # PDF, metadata, validation, ranking, PDF generation
utils/                  # deterministic formula helpers
sample_rfps/             # four reproducible fictional proposal PDFs
outputs/sample_run.json  # complete example evaluation export
tests/                   # scoring, validation, ranking, metadata, persistence tests
.env.example
requirements.txt
```

## Setup (Windows PowerShell)

Use Python 3.10 or newer. From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python -m database.seed
```

If PowerShell blocks venv activation, run the virtual environment's interpreter directly, for example `\.venv\Scripts\python.exe -m streamlit run app.py`.

### Environment variables

Edit `.env` for live model evaluation. Never commit this file.

| Variable | Purpose | Default |
|---|---|---|
| `LLM_API_KEY` | Provider secret; blank selects DEMO mode | blank |
| `LLM_MODEL` | JSON-capable chat model | `gpt-4o-mini` |
| `LLM_BASE_URL` | OpenAI-compatible API base URL | OpenAI API URL |
| `LLM_TIMEOUT_SECONDS` | Per-request timeout | `90` |
| `LLM_TEMPERATURE` | Model sampling temperature | `0` |
| `RFP_DATABASE_PATH` | SQLite database location | `database/rfp_evaluator.db` |

## Run the application

```powershell
streamlit run app.py
```

Open the local URL printed by Streamlit. Navigate to **Criteria** to edit criterion names, descriptions, weights, maximum scores, and active status. Active weights must total exactly 100%. Go to **Evaluate suppliers**, upload multiple PDFs, review each name/date/experience rating, then select **Evaluate Suppliers**.

The four included PDFs are in `sample_rfps/`. To recreate them from source:

```powershell
python tools/generate_sample_pdfs.py
```

To create a fresh deterministic sample run and refresh `outputs/sample_run.json`:

```powershell
python -m tools.create_sample_run
```

## Scoring formulas

Active criteria have a maximum score and weights totaling 100%.

**Absolute weighted score (out of 100):**

```text
SUM((supplier criterion score / configured max score) * criterion weight)
```

**Criterion benchmark:** the highest normalized score observed for that criterion among all suppliers in that batch.

**Criterion gap:** `supplier score - benchmark`.

**Relative performance:** `(supplier score / benchmark) * 100`.

If the benchmark is zero, the relative value is set to 100% for every supplier on that criterion. This neutral value avoids division by zero and ensures a criterion with no observed points does not separate suppliers.

**Peer Performance Index (PPI):** weighted average of criterion relative-performance percentages using the active criterion weights. PPI is a peer comparison index, not a probability or absolute score.

### Tie-break rules

The complete order is sorted by:

1. Higher PPI first.
2. Earlier submission date first.
3. Higher historical experience rating first.
4. Supplier name ascending alphabetically, case-insensitive.

Sequential ranks are assigned only after the full sort. No LLM participates in score arithmetic, benchmark selection, PPI, tie-breaking, or final rank.

## Validation and error handling

Missing criterion results are restored with a score of zero, explicit absent-evidence text, and a warning. Non-numeric/non-finite scores normalize to zero; scores outside the configured range are clipped with warnings. A model-supplied `max_score` never overrides SQLite. Duplicate and unknown criteria, malformed fields, model supplier-name mismatches, invalid risks, and absent evidence remain visible in the result. Malformed JSON is safely recovered only when one complete JSON object can be isolated; otherwise the run fails with a clear message.

Supplier metadata is checked for non-empty unique names, valid non-future ISO dates, experience ratings from 0 to 10, and non-empty file bytes. PDF errors and model API failures/timeouts are shown to the user and the run is marked FAILED in SQLite. Database exceptions are surfaced rather than hidden.

## Testing

```powershell
pytest -q
```

Coverage includes weighted scoring, criterion benchmarks and gaps, relative performance, PPI, zero benchmark handling, PPI/date/experience/name tie-break order, deterministic repeat ordering, alphabetic final tie-break, missing and out-of-range criteria, malformed JSON, invalid metadata, and complete SQLite persistence.

## Deployment (Streamlit Community Cloud)

1. Create a GitHub repository and push the project files. Keep `.env`, `.streamlit/secrets.toml`, and SQLite runtime files out of Git; `.gitignore` excludes them. The four synthetic PDFs and `requirements.txt` are repository files and should be pushed.
2. In Streamlit Community Cloud, select **Create app**, then choose the repository, branch, and root entrypoint `app.py`.
3. The app initializes its SQLite schema and seeds criteria on startup. The database is generated at `RFP_DATABASE_PATH` (default `database/rfp_evaluator.db`); it does not need to be committed.
4. To enable live LLM mode, enter root-level keys in the app's **Advanced settings → Secrets**. Streamlit exposes root-level secret entries as environment variables, which this app reads with `os.getenv`:

   ```toml
   LLM_API_KEY = "your-provider-key"
   LLM_MODEL = "gpt-4o-mini"
   LLM_BASE_URL = "https://api.openai.com/v1"
   LLM_TIMEOUT_SECONDS = "90"
   LLM_TEMPERATURE = "0"
   ```

   Leave `LLM_API_KEY` unset to use deterministic DEMO mode. Do not put live secrets in the repository or its README.
5. Wait for the deployment to complete, open the generated `*.streamlit.app` URL, and run a batch with the four PDFs. Confirm the leaderboard, scorecards, JSON download, and run-history persistence. Check app logs from the Cloud workspace if startup fails.

The included SQLite database is local-file persistence. Streamlit Community Cloud's filesystem is not a managed durable database, so evaluation history may not survive redeployment or instance replacement. For durable public use, configure a persistent external SQLite volume or migrate the persistence layer to a managed database. A public deployment was not created as part of this repository implementation because that requires access to the user's GitHub and Streamlit accounts.

## Example screenshots

Run the app locally and capture the Overview, Criteria editor, Leaderboard, and Detailed scorecard screens here for a course submission. The core UI is responsive and these screenshots are intentionally left environment-specific.

## Assumptions and limitations

- Uploaded PDFs must contain selectable text; OCR for scanned documents is not implemented.
- LLM scores are qualitative model judgments and should be reviewed by procurement staff. Evidence excerpts and warnings are exposed for that review.
- The demo evaluator is deterministic and intended only to make classroom demonstrations reproducible without credentials. It is not a substitute for a configured LLM or human procurement decision.
- The sample experience rating is batch metadata entered by the user; the Evaluation Agent does not invent or infer it.
- The app enforces 0–10 historical experience ratings and non-future submission dates.
- SQLite is suitable for a local classroom project, not concurrent production procurement workloads.
