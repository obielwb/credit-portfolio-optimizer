# Credit Portfolio Optimizer

A full-stack decision-support system for assigning pre-approved credit limits across a portfolio. The project combines customer segmentation, mathematical optimization, asynchronous job processing, persistent execution history, and an analytics interface.

This is a sanitized portfolio edition of a collaborative academic project. Company names, personal information, internal reports, proprietary analyses, original datasets, branding, and delivery-process artifacts were intentionally excluded. The included sample is synthetic and the configuration values are illustrative; nothing in this repository represents a real institution's policy or production data.

## Technical highlights

- Portfolio optimization with custom Simplex, OR-Tools Simplex, and Branch-and-Bound implementations.
- K-Means and MiniBatch K-Means segmentation with configurable policy assignment.
- FastAPI backend with PostgreSQL persistence and typed request/response contracts.
- RabbitMQ worker for asynchronous optimization runs and progress tracking.
- MinIO object storage for uploaded datasets and generated results.
- Next.js 14 and TypeScript interface for configuration, execution, history, analytics, and run comparison.
- Unit, integration, end-to-end, performance, and stress test suites retained as implementation references.

## Architecture

```text
Next.js frontend (:3000)
          |
          v
FastAPI API (:8000) -----> PostgreSQL
          |                    execution metadata and results
          +----------------> MinIO
          |                    uploaded files and exports
          +----------------> RabbitMQ -----> Optimization worker
                                               |
                                               +--> feature engineering
                                               +--> K-Means/MiniBatch clustering
                                               +--> Simplex / OR-Tools / Branch-and-Bound
                                               +--> policy validation and persistence
```

For a deeper component walkthrough, see [Architecture](docs/ARCHITECTURE.md).

## Repository layout

```text
.
├── apps/
│   ├── backend/       # FastAPI API, worker, persistence, storage and queue adapters
│   ├── frontend/      # Next.js application and typed API client
│   └── optimizer/     # Clustering and mathematical optimization pipeline
├── docs/
│   └── ARCHITECTURE.md
└── README.md
```

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or newer
- Node.js 18 or newer
- `uv` for Python dependency management (recommended)

## Run the complete system

Start the API, worker, PostgreSQL, RabbitMQ, and MinIO:

```bash
cd apps/backend
cp .env.example .env
docker compose up -d --build
```

Start the frontend in another terminal:

```bash
cd apps/frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

The credentials in `.env.example` are local-development defaults only. Replace them before using any shared or remotely accessible environment.

## Run the optimizer independently

The optimizer accepts a CSV file without requiring the API infrastructure:

```bash
cd apps/optimizer
python -m pip install -r requirements.txt
PYTHONPATH=. python main.py \
  --input examples/synthetic_clients.csv \
  --algorithm simplex
```

Available algorithms:

- `simplex`: custom linear-programming implementation.
- `simplex_ortools`: OR-Tools-backed linear optimization.
- `branch_bound`: integer/discrete search using Branch and Bound.

The synthetic input contains opaque client IDs and generated values only.

## Local backend development

With PostgreSQL, RabbitMQ, and MinIO available locally:

```bash
cd apps/backend
cp .env.example .env
uv sync
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Run the worker in a second terminal:

```bash
cd apps/backend
uv run python src/worker.py
```

## API workflow

1. Upload a synthetic CSV and select an optimization algorithm.
2. Poll the queued run while the worker performs ingestion, segmentation, and optimization.
3. Read the persisted portfolio recommendations and aggregate metrics.
4. Compare completed runs or export a report.

The API intentionally exposes English-only routes, fields, states, validation messages, and generated report labels in this public edition.

## Data and privacy boundary

- No original company dataset, benchmark output, slide deck, interview, persona, internal process description, or business analysis is included.
- No institution logo, employee/student profile, private URL, or identifying attribution is included.
- Sample identifiers are random opaque values and do not represent real people.
- Historical Git data is not part of the public repository; the portfolio edition starts from a new root commit.

## Scope note

This repository demonstrates engineering and optimization techniques. It is not a production credit policy, underwriting recommendation, or claim about any real portfolio's performance.
