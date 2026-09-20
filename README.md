# EatFood AI Data Analytics — End-to-End Data Engineering Project

An end-to-end batch data pipeline that takes food-delivery data (restaurants, users, menu, orders, order items, reviews) from raw CSVs to AI-powered analytics:

**CSV data → Amazon S3 → Snowflake → dbt → Airflow → AI (OpenAI) → Streamlit**

Raw files land in an S3 data lake and load into Snowflake through a storage integration. dbt transforms them through medallion layers: RAW (Bronze), cleaned STAGING (Silver) and business-ready MARTS (Gold). Apache Airflow orchestrates everything as one daily DAG. An AI layer on top uses OpenAI for review enrichment, RAG over reviews, and text-to-SQL

## Architecture

![Architecture](docs/architecture.png)

| Layer | Where | What |
|---|---|---|
| Source | `DATA/` (local) | Dimension CSVs (restaurants, users, food, menu) + fact files (orders, order items, reviews) |
| Lake | Amazon S3 | One bucket, `raw/<table>/` folder per CSV |
| Bronze | Snowflake `RAW` | `COPY INTO` from S3 via a keyless storage integration |
| Silver | Snowflake `STAGING` | dbt staging views: clean, type, rename every source |
| Gold | Snowflake `MARTS` | Dimensions, incremental facts (MERGE), business marts |
| AI | Snowflake `AI` | LLM-enriched reviews (sentiment/topic), RAG chat, text-to-SQL |
| Orchestration | Airflow (Docker) | One daily DAG: load → transform → enrich → AI mart |

## Tech stack

Python · Pandas · Amazon S3 · Snowflake · dbt (dbt-snowflake) · Apache Airflow (Docker) · OpenAI (`gpt-4o-mini`, `text-embedding-3-small`) · Streamlit

## Dataset

The full dataset is about 2.3 GB, so the large files are **not committed** to this repo (GitHub's limit is 100 MB per file).

| File | Size | In repo? |
|---|---|---|
| `orders.csv` | ~1.27 GB | No — download link below; `orders_sample.csv` (10k rows) included |
| `order_items.csv` | ~911 MB | No — download link below; `order_items_sample.csv` (10k rows) included |
| `menu.csv` | ~63 MB | Yes |
| `restaurant.csv` | ~45 MB | Yes |
| `reviews.csv` | ~24 MB | Yes |
| `food.csv` | ~16 MB | Yes |

**Full data download:** `<ADD LINK: Kaggle / Google Drive / Hugging Face>` — place the files under `DATA/`.

The sample files contain only the first 10,000 rows. They are for checking the schema, not for statistics.

## Repository structure

```
├── airflow/          # Airflow on Docker: Dockerfile, docker-compose, DAG (zomato_batch.py)
├── zomato/           # dbt project: staging views, dimensions, incremental facts, marts, tests
├── ai/               # enrich_reviews.py, rag_chat.py, text_to_sql.py (Streamlit apps)
├── snowflake/        # Setup SQL, run in order 01 → 05
├── aws/iam/          # IAM policy + trust policies for the S3 ↔ Snowflake handshake
├── DATA/             # CSVs (large files excluded, see Dataset)
└── docs/             # architecture diagram
```

## How the pipeline works

### 1. Data lands in S3
The CSVs are uploaded to `s3://<BUCKET>/raw/<table>/`, one folder per table.

### 2. S3 → Snowflake: keyless handshake
Snowflake reads the bucket with no stored keys, using a **storage integration** and an **IAM role**. Order matters: create the AWS policy and role, create the Snowflake integration pointing at the role ARN, run `DESC INTEGRATION` to get the IAM user ARN and external ID, then paste both into the role's trust policy. Never re-run `CREATE OR REPLACE` on the integration afterwards, because it regenerates the external ID and breaks the trust.

### 3. Load: COPY INTO
DDL in `snowflake/04_raw_tables.sql` matches each CSV's column order. `05_copy_into.sql` loads each file from the stage into the `RAW` tables.

### 4. Transform: dbt (medallion)
- **Staging (Silver):** one view per source; cleans messy fields, lowercases emails, derives flags such as `is_delivered`.
- **Dimensions (Gold):** restaurants, customers (with age segments), food, and a generated date calendar.
- **Facts (Gold, incremental):** orders and order items use `materialized='incremental'` with a MERGE strategy, so re-runs process only new rows.
- **Marts (Gold):** daily city revenue (GMV / AOV / cancel rate), restaurant performance, delivery SLA (p50/p90), review insights.
- **Tests:** unique, not_null, relationships, accepted_values, plus a reconciliation test.

### 5. Orchestrate: Airflow
One daily DAG runs the whole pipeline:

```
reload_raw → dbt_build_core → enrich_reviews → dbt_build_ai
```

Credentials are injected as environment variables and never stored in code.

### 6. AI layer
- **LLM enrichment:** `gpt-4o-mini` turns free-text reviews into structured sentiment and topic columns.
- **RAG:** chat with the reviews, with answers grounded in retrieved reviews.
- **Text-to-SQL:** ask the warehouse questions in English; a SELECT-only guard validates the SQL before it runs.

## Running it

```bash
# 1. Snowflake objects + S3 integration: run snowflake/01 → 05 in Snowsight (see aws/iam/ for the AWS side)

# 2. dbt
cd zomato
export SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_PASSWORD=...
dbt debug && dbt build --exclude tag:ai

# 3. Airflow
cd airflow
cp example.env .env        # fill SNOWFLAKE_*, OPENAI_API_KEY, SAMPLE_N
docker compose build && docker compose up -d
# http://localhost:8080 → un-pause zomato_batch → Trigger

# 4. AI apps
export OPENAI_API_KEY=sk-...
python ai/enrich_reviews.py
streamlit run ai/rag_chat.py
streamlit run ai/text_to_sql.py
```
