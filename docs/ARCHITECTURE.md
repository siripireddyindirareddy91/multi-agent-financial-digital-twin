# FINSTRESS AI architecture

Next.js App Router provides eighteen functional workspace pages. Client state uses Zustand; financial data is fetched from authenticated Python REST endpoints. React Hook Form and Zod validate sign-in; Pydantic validates all financial writes. Recharts visualizes API calculations; React Flow provides an illustrative synthetic exposure network. Framer Motion handles restrained entry transitions.

FastAPI exposes OpenAPI at `/docs` locally. SQLAlchemy stores users, twins, scenarios, runs, agent executions, approval requests, audit logs, reports and preferences. JSON snapshots preserve original inputs with each simulation. This is intentionally a compact schema: asset categories, findings and decisions are embedded records rather than the fully normalized sixteen-table design in the original brief. PostgreSQL is the production target. SQLite supplies a local fallback; Vercel `/tmp` storage is ephemeral and shared demo data may reset.

The LangGraph state graph executes economic -> twin -> credit -> market -> liquidity -> capital -> simulation -> orchestrator -> explainability -> human-review nodes. Each node has an identity, role, input envelope, output and measured duration. Actual node completions are persisted, then the UI polls for those executions. Failures mark the run as failed and are logged. Calculations are deterministic; no hosted LLM is used or required.

Background tasks execute within the serverless request lifecycle. They are suitable for the bounded demo, not a durable distributed job queue. For larger workloads move execution to a worker queue and dedicated Python service. No WebSocket support is claimed on Vercel.

Authentication uses PBKDF2-SHA256 salted passwords and eight-hour JWTs. Every record access is scoped by owner. Registration creates analyst accounts; manager/administrator roles alone can approve/reject. Auditors cannot mutate. No public role escalation endpoint exists. Role provisioning is an administrator database operation. The documented shared demo is a manager on synthetic records only.

Report snapshots hold completed results; downloads require authorization and return generated PDF/CSV. Audit entries capture all writes and decisions. Approvals are advisory and never trigger real financial actions.

## Financial assumptions

All currency is INR crore. Assets = cash + loans + government securities + corporate bonds + equities. Liabilities = deposits + wholesale funding. Equity = assets - liabilities. The provided demo's remaining 5,000 crore of assets is allocated 3,000 to bonds and 2,000 to equities.

PD uses seeded synthetic-trained logistic regression with macro inputs. Lifetime PD = 1-(1-annual PD)^(months/12). LGD = min(85%,40% + property-decline/200). ECL = PD x LGD x loans. Government duration is four years; corporate duration is three years; equity shocks apply only to the equity bucket. Wholesale rate shocks add funding costs over the selected horizon. Withdrawals repay deposits and reduce both assets and liabilities, without being counted as P&L losses.

RWA = loans + 50% corporate bonds + equities; it is held constant under stress. CAR = post-loss equity/RWA. HQLA = cash + 85% post-shock government securities minus withdrawals, floored at zero. Modeled 30-day outflows = 5% remaining deposits + 15% wholesale funding. LCR = HQLA/outflows. This is a simplified research approximation, not a regulatory LCR implementation.

Resilience score weights normalized capital 40%, liquidity 35%, credit quality 25%. CAR reference is 12%; LCR reference is 100%. This is not an official rating. Inflation is scenario context rather than an independent loss multiplier. Operational losses and dynamic balance-sheet responses are excluded. Timeline charts linearly interpolate terminal outcomes; they are not independently estimated monthly forecasts.

Monte Carlo uses a seeded Gaussian common factor plus independent shocks, positive pairwise correlation 0.4225, and documented scenario clipping. Outputs include loss histogram, quantiles, VaR, tail mean, capital/resilience percentiles and liquidity shortfall fraction. Mean-loss intervals use a normal approximation; they do not measure model validity. No fabricated SHAP or actual bank forecasts are presented.

## Deployment limitations

The application is a functional research demonstration, not certified enterprise infrastructure. Configure PostgreSQL and a stable JWT_SECRET for durability and consistent sessions across Vercel instances. SQLite in `/tmp` is intentionally identified as temporary. Rate limiting is per process; use an external shared limiter before public production use. Shared demo credentials must be disabled using ENABLE_DEMO=false for a private institutional deployment. Docker configuration is supplied; execution requires Docker and is verified only when explicitly recorded in validation results.
