# Event Registration & Ticketing System

A serverless REST API that replaces Microsoft Forms + Excel for event
registration, built entirely on AWS managed services.

Capstone project — Azubi Africa AWS Cloud Engineering Programme.

## Live Demo

**Live app:** https://d2xxupubh9fm1w.cloudfront.net

**API Base URL:** `https://xqga6ovdbb.execute-api.us-east-1.amazonaws.com/prod`

curl https://xqga6ovdbb.execute-api.us-east-1.amazonaws.com/prod/events


## Problem

Manual event registration using Forms + Excel doesn't scale: no real-time
capacity tracking, no automated confirmations, no audit trail, and no way
to query a participant's registrations. This project replaces that process
with a serverless API that is cheap to run (pay-per-use, Free Tier eligible),
scales automatically, and is fully defined as code.

## Architecture

┌─────────────────┐
GitHub ───push──▶ GitHub Actions │ (test + deploy via OIDC)
└────────┬─────────┘
│ sam deploy
▼
Client ──HTTPS──▶ API Gateway (REST) ──▶ Lambda (Python 3.13) ──▶ DynamoDB
│ │
│ └──▶ SNS (confirmation email)
▼
CloudWatch (Logs, Metrics, Alarms)


**Services used:** API Gateway, AWS Lambda, DynamoDB, SNS, CloudWatch,
IAM, GitHub Actions, AWS SAM, S3 + CloudFront (frontend hosting).

## API Endpoints

| Method | Path                     | Description                           |
| ------ | ------------------------ | ------------------------------------- |
| POST   | `/register`              | Register for an event                 |
| GET    | `/events`                | List all events (optional `?status=`) |
| GET    | `/registrations/{email}` | View a participant's registrations    |
| DELETE | `/registration/{id}`     | Cancel a registration                 |

### Example requests

**Register**

curl -X POST https://xqga6ovdbb.execute-api.us-east-1.amazonaws.com/prod/register
-H "Content-Type: application/json"
-d '{"eventId":"evt-001","name":"Ella Martey","email":"ella@example.com"}'


**List events**

curl https://xqga6ovdbb.execute-api.us-east-1.amazonaws.com/prod/events


**View a participant's registrations**

curl https://xqga6ovdbb.execute-api.us-east-1.amazonaws.com/prod/registrations/ella@example.com


**Cancel a registration**

curl -X DELETE https://xqga6ovdbb.execute-api.us-east-1.amazonaws.com/prod/registration/<registrationId>


## Data Model

**EventsTable** — partition key `eventId`

| Field    | Type                                            |
| -------- | ----------------------------------------------- |
| eventId  | String                                          |
| name     | String                                          |
| date     | String                                          |
| location | String                                          |
| capacity | Number                                          |
| status   | String (`AVAILABLE` \| `LIMITED` \| `SOLD_OUT`) |

**RegistrationsTable** — partition key `registrationId`, GSI `email-index` on `email`

| Field          | Type                                |
| -------------- | ----------------------------------- |
| registrationId | String                              |
| eventId        | String                              |
| email          | String                              |
| name           | String                              |
| status         | String (`CONFIRMED` \| `CANCELLED`) |
| createdAt      | String (ISO 8601)                   |

## Repository Structure

event-ticketing-system/
├── template.yaml # AWS SAM infrastructure-as-code
├── samconfig.toml # Default sam deploy parameters
├── requirements.txt # Lambda runtime dependencies
├── src/
│ ├── register.py # POST /register
│ ├── list_events.py # GET /events
│ ├── get_registrations.py # GET /registrations/{email}
│ ├── cancel_registration.py # DELETE /registration/{id}
│ └── common/response.py # Shared CORS/response helpers
├── scripts/seed_events.py # Loads sample events into DynamoDB
├── frontend/index.html # Live registration UI (S3 + CloudFront)
├── tests/test_lambdas.py # Unit tests (moto-mocked AWS)
└── .github/workflows/
├── test.yml # Runs on every push/PR
└── deploy.yml # Deploys to AWS on push to main


## Prerequisites

- AWS account (Free Tier is sufficient)
- AWS CLI configured (`aws configure`)
- AWS SAM CLI
- Python 3.13
- A GitHub repository (for CI/CD)

## Phase 1 — Infrastructure Foundation

The infrastructure is defined entirely in `template.yaml` using AWS SAM,
which compiles down to CloudFormation. It provisions:

- An **API Gateway** REST API (regional endpoint) with CORS enabled
- **4 Lambda functions**, one per endpoint, each scoped to the exact
DynamoDB/SNS permissions it needs (least privilege — see IAM section)
- **2 DynamoDB tables** on-demand billing (pay-per-request, Free Tier friendly)
- An **SNS topic** for confirmation emails
- **CloudWatch alarms** for error rate and duration

Deploy it locally with the guided flow:

sam build
sam deploy --guided


## Phase 2 — API Development

Each endpoint is an isolated Lambda function under `src/`:

- **`register.py`** — validates the payload (required fields, email format,
length limits), confirms the event exists and isn't sold out, writes a
conditional put to prevent duplicate registrations, and publishes a
best-effort SNS confirmation.
- **`list_events.py`** — scans (paginated) the events table, with an
optional `?status=` filter.
- **`get_registrations.py`** — queries the `email-index` GSI so lookups by
email don't require a full table scan.
- **`cancel_registration.py`** — soft-deletes by flipping `status` to
`CANCELLED` rather than removing the record, preserving the audit trail.

Seed the events table with sample data after deploy:

python scripts/seed_events.py <events-table-name> --region us-east-1


## Phase 3 — Automation & CI/CD

Two GitHub Actions workflows live in `.github/workflows/`:

- **`test.yml`** — runs on every push and PR. Installs dependencies, runs
the `pytest` suite (DynamoDB and SNS mocked with `moto`), and lints with
`flake8`.
- **`deploy.yml`** — runs on push to `main`. Calls `test.yml` as a
reusable workflow first (deploy is blocked if tests fail), then
authenticates to AWS via **OIDC** and runs `sam build && sam deploy`.

## Phase 4 — Monitoring & Security

- **CloudWatch Logs** on every Lambda (`/aws/lambda/<function-name>`)
- **CloudWatch Alarms** — API 5xx error rate, Lambda errors, Lambda duration
- **X-Ray tracing** enabled on all functions
- **IAM least privilege** — scoped SAM policy templates per function, not
one shared role
- **OIDC-based deploy** — GitHub Actions authenticates to AWS with short-lived
tokens, no long-lived access keys stored as secrets
- **Input validation** on every endpoint

## Phase 5 — Deployment & Cost Optimisation

- **On-demand DynamoDB billing** — pay per request, Free Tier friendly
- **Lambda memory tuned to 128 MB**
- **Regional API Gateway endpoint** — avoids the CloudFront edge layer on
the API itself, keeping the request path simple
- **Reusable CI workflow** — `deploy.yml` calls `test.yml` instead of
duplicating steps
- **Frontend hosted on S3 + CloudFront** — static hosting behind a CDN
for free HTTPS and global caching

### Tearing everything down

sam delete --stack-name event-ticketing-system


## Running Tests Locally

pip install -r requirements.txt -r tests/requirements-test.txt
pytest tests/ -v


## Roadmap / Possible Extensions

- Cognito-based auth so `/registrations/{email}` only returns the caller's
own data
- DynamoDB Streams → Lambda to auto-flip `status` to `SOLD_OUT` at capacity
- API keys + usage plans for rate-limited public access
- CloudWatch dashboard for at-a-glance system health

## Author

**Emmanuella Odetsi Martey** Azubi Africa AWS Cloud Engineering Programme