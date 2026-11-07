# FINSTRESS AI

Live application: https://multi-agent-financial-digital-twin.vercel.app

Production storage: free Neon PostgreSQL, connected through Vercel. A stable production JWT secret is configured. The SQLite fallback described below applies only when DATABASE_URL is omitted. Automatic GitHub deployment linking needs repository access granted to the Vercel GitHub integration; direct CLI deployment is configured and works.

Multi-Agent Financial Digital Twin & Stress Testing Platform. Functional research demonstration using **synthetic institution data**, transparent Python financial calculations and ten actual LangGraph agent nodes. It is not a validated regulatory or investment system.

## Run locally

Prerequisites: Python 3.12+, Node.js 22+, optionally PostgreSQL 16 / Docker.

```powershell
npm ci
python -m pip install -r requirements.txt
# Terminal 1 (SQLite works without configuration)
python -m uvicorn backend.app.main:app --reload --port 8000
# Terminal 2
npm run dev
```

Open http://localhost:3000. API documentation: http://localhost:8000/docs.

**Demo login:** `demo@finstress.ai` / `FinstressDemo!2026` (synthetic shared Risk Manager workspace). Registered accounts receive analyst access and their own seeded institution/scenarios; they cannot approve recommendations. Set `ENABLE_DEMO=false` to disable demo creation in a fresh private database. Demo users already present must be removed separately.

## Configuration

Copy `.env.example` as reference. Python reads shell environment variables; `.env` is consumed by Docker Compose. For direct Python execution export the variables in your shell (it does not automatically read `.env`).

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection string. Omit for SQLite local fallback. |
| `JWT_SECRET` | Stable random signing secret, at least 32 random bytes recommended. Omitted: per-process random key, sessions reset on cold start. |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins. |
| `ENABLE_DEMO` | `true` seeds a documented manager demo account. |
| `DEMO_PASSWORD` | Override shared demo password; default shown above. |
| `API_BACKEND_URL` | Next.js proxy destination when Python is hosted separately. |
| `POSTGRES_PASSWORD` | Local Docker database password. |

No OpenAI API key is required. The current agent implementation intentionally uses deterministic reasoning and a synthetic-trained logistic regression, not a hosted LLM provider. Optional LLM explanation integration is not implemented or claimed.

## Demonstration workflow

1. Sign in and view baseline financial health.
2. Create, edit, duplicate or reset edits to a financial digital twin.
3. Choose a predefined or custom scenario; edit GDP, rates, unemployment, valuation and withdrawal shocks.
4. Run a stress test. Polling displays persisted agent completions, never arbitrary simulated progress.
5. Inspect credit, liquidity, capital, market losses and calculation explanations.
6. Run seeded Monte Carlo (100–5,000 paths), compare scenarios and explore the illustrative network.
7. Record a review rationale and approve/reject recommendations as a manager.
8. Generate and download PDF/CSV reports; inspect audit records.

Amounts are INR crore. Aurelia National Bank is fictional: assets 50,000, liabilities 45,000, equity 5,000. Its remaining 5,000 of assets after loans/cash/government securities is allocated 3,000 corporate bonds and 2,000 equities.

## Project structure

```text
app/                     Next.js App Router, 18 workspace sections
components/              Workspace UI, charts, editable forms, React Flow network
lib/                     Authenticated API and file download clients
api/index.py             Vercel Python / FastAPI entrypoint
backend/app/main.py      REST API, auth, CRUD, simulation jobs, approvals, reports
backend/app/finance.py   Stress engine, credit model, seeded Monte Carlo
backend/app/agents.py    Ten-node LangGraph workflow
backend/app/database.py  SQLAlchemy tables and transaction sessions
backend/app/schemas.py   Pydantic financial input validation
backend/tests/           Financial invariants and authenticated integration tests
backend/alembic/         Initial database migration
docs/ARCHITECTURE.md     Architecture, formulas, assumptions and limitations
Dockerfile*              Backend/frontend container builds
docker-compose.yml       PostgreSQL + API + frontend
vercel.json              Python API routing alongside Next.js
```

## Verify

```powershell
python -m pytest backend/tests -q
npm run typecheck
npm run build
```

Tests check balance reconciliation, ECL identity, no double-counting withdrawals, shock sensitivity, reproducible stochastic results, ten real agent executions, login, tenant isolation, role restrictions, decisions, report downloads and invalid input rejection.

## Docker & migrations

```powershell
$env:JWT_SECRET = 'your-random-secret-at-least-32-bytes'
docker compose up --build
python -m alembic -c backend/alembic.ini upgrade head
```

Schema initialization also runs automatically on first API request. Migration is provided for a new database; avoid running it after independently creating the same schema in a production migration workflow. Docker execution requires a working Docker engine.

## Vercel deployment

```powershell
vercel link
vercel env add JWT_SECRET production
vercel env add DATABASE_URL production
vercel --prod
```

The root includes Next.js and a FastAPI Python serverless function. `/api/*` rewrites to `api/index.py`. For a separate durable Python deployment set `API_BACKEND_URL` and remove the Vercel API rewrite if you intend Next.js to proxy it.

**Durability:** without PostgreSQL, Vercel SQLite uses `/tmp/finstress.db` and is temporary, instance-local storage. Data can disappear on redeploy/cold start and is not shared across instances. A stable JWT secret is essential for session consistency. The UI displays storage limitations. No durable database is provisioned automatically. Bounded simulation jobs use FastAPI background tasks; use a dedicated queue/worker for production scale. Rate limiting is per-process. Reports are generated from saved snapshots and use authenticated downloads.

The original full brief also requested a fully normalized sixteen-table schema, three ML algorithms, optional LLM integration, SHAP when compatible, and a production deployment. This implementation uses a compact snapshot schema, one real logistic model, deterministic explanations, and an illustrative network. It does not claim these omitted enhancements, enterprise certification, or validated forecasts. See [architecture and methodology](docs/ARCHITECTURE.md) for details.
