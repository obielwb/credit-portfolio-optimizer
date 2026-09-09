# Architecture

## System context

The system models credit-limit assignment as an asynchronous data pipeline. A user uploads a synthetic portfolio, selects an algorithm, and submits a run. The API validates and stores the file, publishes a job, and immediately returns a run identifier. A separate worker executes the CPU-bound optimization and records progress and results.

## Backend

The FastAPI application is split into controllers, services, repositories, schemas, and infrastructure adapters:

- **Controllers** define HTTP boundaries for ingestion, optimization, parameters, statistics, comparisons, and health checks.
- **Services** coordinate validation, persistence, analytics, and run lifecycle rules.
- **Repositories** isolate SQLAlchemy access for files, clients, parameters, clusters, runs, and results.
- **Schemas** provide typed request, response, and database contracts.
- **Infrastructure adapters** connect the application to PostgreSQL, RabbitMQ, and MinIO.

Long-running work is deliberately outside the request process. RabbitMQ separates API availability from optimizer runtime, while the worker updates run state so the frontend can provide progressive feedback.

## Optimization pipeline

The optimizer follows five stages:

1. **Ingestion and feature engineering** normalize propensity, probability-of-default, capacity, and optional cohort fields.
2. **Business filtering** removes records that violate configurable eligibility constraints.
3. **Clustering** groups similar records using K-Means or MiniBatch K-Means when portfolio size requires it.
4. **Policy assignment** maps clusters to configurable leverage policies.
5. **Optimization and post-processing** allocate limits, validate portfolio constraints, optionally discretize recommendations, and calculate expected financial outcomes.

The implementation supports three optimization strategies behind a common pipeline contract:

- a custom Simplex solver for the continuous linear model;
- an OR-Tools Simplex adapter for an independent solver implementation;
- Branch and Bound for discrete decision constraints.

## Frontend

The Next.js application uses the App Router and a centralized typed API client. Its primary views cover:

- run configuration and synthetic file upload;
- live job progress;
- portfolio-level KPIs and recommendation inspection;
- execution history and result downloads;
- side-by-side comparison of completed runs.

## Persistence model

PostgreSQL stores metadata and relational results, including uploaded-file records, optimization runs, active parameter sets, cluster summaries, client-level recommendations, and portfolio aggregates. MinIO stores the larger input/output objects. This separation keeps relational queries efficient while preserving downloadable artifacts.

## Public-edition boundary

The architecture and implementation are retained, but all partner-specific context, source datasets, measured business outcomes, internal process analysis, branded prototypes, and original project history were removed. Default values and synthetic examples are illustrative only.
