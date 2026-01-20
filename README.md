# Medical Telegram Data Warehouse

# A Complete Data Pipeline for Ethiopian Pharmaceutical Market Analysis

📋 Project Overview

This project implements a production-grade data pipeline for monitoring Ethiopian medical Telegram channels. 

The system extracts, transforms, and analyzes data from Telegram e-commerce channels to provide actionable insights for Kara 

Solutions' market intelligence needs.

Key Features

Automated Data Collection: Scrapes Telegram channels daily using Telethon API

Computer Vision Enrichment: YOLO object detection categorizes product images

Modern Data Stack: PostgreSQL + dbt + FastAPI + Dagster orchestration

Analytical API: RESTful endpoints for business intelligence

Production Orchestration: Scheduled pipelines with monitoring and error handling

Complete Testing: Unit tests, dbt data tests, and integration tests

🏗️ System Architecture

text

flowchart LR
    %% ======================
    %% EXTRACT
    %% ======================
    A[Telegram Scraper] -->|Messages| B[(Raw Data)]
    A -->|Images| C[Image Files]

    %% ======================
    %% COMPUTER VISION
    %% ======================
    C --> D[YOLO Detection]
    D --> E[CV Enrichment]

    %% ======================
    %% TRANSFORM
    %% ======================
    B --> F[dbt Transformations]
    E --> F
    F --> G[Star Schema Models]

    %% ======================
    %% LOAD
    %% ======================
    G --> H[(PostgreSQL Warehouse)]

    %% ======================
    %% ANALYTICS
    %% ======================
    H --> I[FastAPI Analytics]
    H --> J[BI Dashboards]

    %% ======================
    %% ORCHESTRATION
    %% ======================
    K[Dagster Orchestration]
    K -. Schedule .-> A
    K -. Monitor .-> F
    K -. Retry .-> D
    K -. Alert .-> I


🚀 Quick Start

Prerequisites

bash

# Required Software

- Docker 20.10+ and Docker Compose 2.0+

- Python 3.10+ (for local development)

- Git

- Telegram account with phone number

# Storage Requirements

- Minimum 10GB free disk space

- 4GB RAM for Docker containers

- Stable internet connection

1. Clone and Setup

bash

# Clone repository

git clone https://github.com/Saronzeleke/Medical-telegram-warehouse-week8.git

cd medical-telegram-warehouse-week8

# Create environment file

cp .env.example .env

# Edit .env with your credentials

nano .env

2. Configure Environment (.env)

bash

# Telegram API Credentials (GET FROM: https://my.telegram.org)

TELEGRAM_API_ID=your_api_id_here

TELEGRAM_API_HASH=your_api_hash_here

TELEGRAM_PHONE=+251XXXXXXXXX  # Ethiopian format: +251 followed by 9 digits

# PostgreSQL Database

POSTGRES_USER=medical_user

POSTGRES_PASSWORD=write secure password 

POSTGRES_DB=medical_warehouse

POSTGRES_HOST=postgres

POSTGRES_PORT=5432


3. Start All Services

bash

# Build and start all containers

docker-compose up --build -d

# Verify services are running

docker-compose ps

# Expected output:

# NAME                          STATUS              PORTS

# medical-fastapi-1             running             0.0.0.0:8000->8000/tcp

# medical-postgres-1            running             0.0.0.0:5432->5432/tcp

# medical-dagster-webserver-1   running             0.0.0.0:3000->3000/tcp

📁 Project Structure

text

medical-telegram-warehouse/

├── .vscode/ 

├── .github/workflows/          # CI/CD: Unit tests on push

├── api/                        # FastAPI Application

│   ├── __init__.py

│   ├── main.py                 # API endpoints (Task 4)

│   ├── database.py             # Database connection (FIXED BELOW)

│   ├── schemas.py              # Pydantic models (Task 4)

│   ├── crud.py                 # Database operations (Task 4)

│   └── models.py               # SQLAlchemy models

├── data/                       # Data storage

    └── processed/

│   └── raw/

│       ├── telegram_messages/  # Partitioned JSON: YYYY-MM-DD/channel.json

│       └── images/             # Downloaded: channel_name/message_id.jpg

├── logs/                       # Application logs

│   ├── scraper_YYYYMMDD.log

│   ├── yolo_YYYYMMDD.log

│   └── postgress_loader.log

├── medical_warehouse/          # dbt Project (Task 2)

│   ├── models/

│   │   ├── staging/            # Cleaning models

│   │   │   ├── stg_telegram_messages.sql

│   │   │   └── schema.yml

│   │   └── marts/              # Star schema

│   │       ├── dim_channels.sql

│   │       ├── dim_dates.sql

│   │       ├── fct_messages.sql

│   │       ├── fct_image_detections.sql  # Task 3

│   │       └── schema.yml

│   ├── tests/                  # Custom dbt tests

│   │   ├── assert_no_future_messages.sql

│   │   ├── assert_positive_views.sql

│   │   └── assert_valid_image_categories.sql

│   ├── dbt_project.yml

│   └── profiles.yml

├── pipeline/                   # Dagster Orchestration (Task 5)

│   └── dagster_pipeline.py

├── src/                        # Source code

│   ├── scraper.py              # Telegram scraper (Task 1)

│   └── yolo_detect.py          # YOLO image analysis (Task 3)

├── scripts/

│   └── load_raw_to_postgres.py # PostgreSQL loader (Task 2)

├── tests/                      # Unit tests

├── notebooks/                  # Jupyter notebooks for analysis

├── docker-compose.yml          # Main services

├── docker-compose.dagster.yml  # Orchestration services

├── Dockerfile

├──Dockerfile.dbt

├──docker_compose.dagster.yml 

├── requirements.txt            # Python dependencies

├── .env                        # Environment variables

└── README.md                   # This file

🔧 Complete Implementation Guide

**Task 1 & 2: Data Pipeline Foundation (Already Complete)**

Your Tasks 1 & 2 are implemented and functional:

Verification Steps:

bash

# Test Telegram scraper

docker-compose exec dbt-service python -m src.scraper

# Check scraped data

ls -la data/raw/telegram_messages/$(date +%Y-%m-%d)/

# Load to PostgreSQL

docker-compose exec dbt-service python scripts/load_raw_to_postgres.py

# Run dbt transformations

docker-compose exec dbt-service bash -c "cd medical_warehouse && dbt run"

# Test dbt models

docker-compose exec dbt-service bash -c "cd medical_warehouse && dbt test"

# View dbt documentation

docker-compose exec dbt-service bash -c "cd medical_warehouse && dbt docs serve"

# Access at: http://localhost:8080

**Task 3: Data Enrichment with YOLO**

Install YOLO Dependencies:

bash

# Update requirements

docker-compose exec dbt-service pip install ultralytics opencv-python torch torchvision

# Or rebuild with updated requirements

docker-compose down

docker-compose up --build -d

Run YOLO Image Analysis:

bash

# Analyze downloaded images

docker-compose exec dbt-service python -m src.yolo_detect --max-images 50

# Check results

ls -la data/processed/yolo_detections/

cat data/processed/yolo_detections/latest_detections.csv | head -5

# Load YOLO results to dbt

docker-compose exec dbt-service bash -c "cd medical_warehouse && dbt run --select fct_image_detections"

bash

# Start API service (if not already running)

docker-compose up fastapi -d

# Or restart if needed

docker-compose restart fastapi

Test API Endpoints:

bash

# Health check

curl "http://localhost:8000/api/health"

# Top products analysis

curl "http://localhost:8000/api/reports/top-products?limit=5&days=30"

# Channel activity

curl "http://localhost:8000/api/channels/tikvah_pharma/activity?period=7d"

# Search messages

curl "http://localhost:8000/api/search/messages?query=paracetamol&limit=10"

# Visual content statistics

curl "http://localhost:8000/api/reports/visual-content?group_by=channel"

# View API documentation

# Open browser: http://localhost:8000/docs

API Endpoints Summary:

Endpoint	Method	Description	Example

/api/health	GET	System health check	curl http://localhost:8000/api/health

/api/reports/top-products	GET	Most mentioned products	?limit=10&days=30&channel_name=tikvah_pharma

/api/channels/{name}/activity	GET	Channel activity trends	/api/channels/tikvah_pharma/activity?period=7d

/api/search/messages	GET	Search messages	?query=paracetamol&limit=20&has_image=true

/api/reports/visual-content	GET	Image analysis stats	?group_by=channel&min_confidence=0.5

/api/reports/engagement-trends	GET	Engagement trends	?metric=views&window=day

Task 5: Dagster Pipeline Orchestration

Start Dagster Services:

bash

# Start Dagster with orchestration

docker-compose -f docker-compose.yml -f docker-compose.dagster.yml up -d

# Check Dagster services

docker-compose ps | grep dagster

# Access Dagster UI: http://localhost:3000

Run Complete Pipeline:

bash

# Method 1: Via Dagster UI

# 1. Open http://localhost:3000

# 2. Navigate to "Deployment" → "Jobs"

# 3. Click "medical_telegram_pipeline"

# 4. Click "Launchpad" → "Launch Run"


# Method 2: Command line

docker-compose exec dagster-webserver python pipeline/dagster_pipeline.py --run

# Method 3: Test run (limited data)

docker-compose exec dagster-webserver python pipeline/dagster_pipeline.py --test

Pipeline Schedule:

Daily: 2 AM Addis Ababa time - Incremental data collection

Weekly: Sunday midnight - Full refresh with YOLO analysis

On-demand: Manual triggers via UI or API

Monitor Pipeline:

bash

# View pipeline logs

docker-compose logs dagster-daemon

# Check pipeline summaries

ls -la data/processed/pipeline_summaries/

# View latest run summary

cat data/processed/pipeline_summaries/run_*.json | tail -1 | python -m json.tool

📊 Data Models & Schema

Star Schema Design

text

┌─────────────────┐      ┌─────────────────┐
│  dim_channels   │◄────┤                 │
│  • channel_key  │      │  fct_messages   │
│  • channel_name │      │  • message_id   │
│  • channel_type │      │  • channel_key  │
│  • avg_views    │      │  • date_key     │
└─────────────────┘      │  • view_count   │
                         │  • has_image    │
┌─────────────────┐      └────────┬────────┘
│   dim_dates     │               │
│  • date_key     │◄──────────────┘
│  • full_date    │
│  • is_weekend   │      ┌─────────────────┐
│  • month_name   │      │ fct_image_detections │
└─────────────────┘      │  • detection_id │
                         │  • image_category│
                         │  • confidence   │
                         └─────────────────┘

Key Tables:

1. dim_channels

Channel metadata with performance metrics.

2. dim_dates

Date dimension for temporal analysis.

3. fct_messages

Core fact table with message-level metrics.

4. fct_image_detections (Task 3)

YOLO analysis results with image categorization.


🧪 Testing & Validation

Run Complete Test Suite:

bash

# Unit tests

docker-compose exec dbt-service pytest tests/ -v

# dbt data tests

docker-compose exec dbt-service bash -c "cd medical_warehouse && dbt test"

# API tests

curl "http://localhost:8000/api/health"

curl "http://localhost:8000/api/reports/top-products?limit=1"

# Pipeline test

docker-compose exec dagster-webserver python pipeline/dagster_pipeline.py --test

Custom dbt Tests:

assert_no_future_messages.sql: No messages with future dates

assert_positive_views.sql: View counts are non-negative

assert_valid_image_categories.sql: Image categories are valid

🐛 Troubleshooting Guide

Common Issues:

1. Telegram API Authentication
bash

# Check credentials

echo "API_ID: $TELEGRAM_API_ID"

echo "API_HASH: $TELEGRAM_API_HASH"

# Test authentication

docker-compose exec dbt-service python -c "
from telethon import TelegramClient
import asyncio, os

async def test():
    async with TelegramClient('test', int(os.getenv('TELEGRAM_API_ID')), os.getenv('TELEGRAM_API_HASH')) as client:
        await client.send_message('me', 'Test message')
        print('Authentication successful')

asyncio.run(test())
"

2. Database Connection Issues

bash

# Test PostgreSQL connection

docker-compose exec postgres pg_isready

# Check tables

docker-compose exec postgres psql -U medical_user -d medical_warehouse -c "\dt marts.*"

# Reset database (WARNING: deletes data)

docker-compose down -v

docker-compose up -d

3. YOLO Detection Issues

bash

# Check if images exist

ls -la data/raw/images/*/*.jpg | head -5

# Test YOLO with single image

docker-compose exec dbt-service python -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
results = model('https://ultralytics.com/images/bus.jpg')
print('YOLO test successful')
"

4. API Connection Issues

bash

# Check FastAPI logs

docker-compose logs fastapi

# Test API directly

curl -v "http://localhost:8000/api/health"

# Check database.py configuration

docker-compose exec fastapi python -c "
from api.database import check_database_connection
print('DB connection:', check_database_connection())
"

5. Dagster Pipeline Issues

bash

# Check Dagster logs

docker-compose logs dagster-webserver

docker-compose logs dagster-daemon

# Restart Dagster

docker-compose restart dagster-webserver dagster-daemon

# Check pipeline definitions

docker-compose exec dagster-webserver python pipeline/dagster_pipeline.py --test

📈 Monitoring & Maintenance

Daily Operations:

bash

# Check pipeline status

docker-compose ps

# View latest logs

tail -f logs/scraper_$(date +%Y%m%d).log

tail -f logs/api_$(date +%Y%m%d).log

# Check disk usage

docker system df

du -sh data/

# Backup database

docker-compose exec postgres pg_dump -U medical_user medical_warehouse > backup_$(date +%Y%m%d).sql

Performance Monitoring:

sql

-- Database performance
SELECT 
    schemaname, tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname IN ('raw', 'staging', 'marts')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Data freshness
SELECT 
    channel_name,
    MAX(message_date) as latest_message,
    CURRENT_DATE - MAX(message_date::date) as days_since_last
FROM staging.stg_telegram_messages 
GROUP BY channel_name;

🚢 Deployment

Environment Configuration:

bash

# Production .env.production

TELEGRAM_API_ID=production_api_id

TELEGRAM_API_HASH=production_api_hash

TELEGRAM_PHONE=+2519XXXXXXXX

POSTGRES_USER=medical_prod_user

POSTGRES_PASSWORD=strong_production_password

POSTGRES_DB=medical_warehouse_prod

# Enable production features

API_RATE_LIMIT=100/hour

ENABLE_CACHE=true

LOG_LEVEL=WARNING

Docker Production Stack:

bash

# Deploy with production compose

docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Enable auto-restart

docker-compose restart --policy always medical-fastapi-1

Backup Strategy:

bash

# Daily backup script (cron job)

#!/bin/bash

DATE=$(date +%Y%m%d)

BACKUP_DIR="/backups/medical_warehouse"

# Database backup

docker-compose exec -T postgres pg_dump -U medical_user medical_warehouse > $BACKUP_DIR/db_$DATE.sql

# Data backup

tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/raw/

# Rotate old backups 

find $BACKUP_DIR -name "*.sql" -mtime +30 -delete

find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

📚 API Documentation

Interactive Documentation:

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

dbt Docs: http://localhost:8080 (when serving)

Dagster UI: http://localhost:3000

🤝 Contributing & Development

Development Workflow:

bash

# 1. Create feature branch

git checkout -b feature/new-analysis

# 2. Make changes with tests

# 3. Run test suite

docker-compose exec dbt-service pytest tests/ --cov=src

docker-compose exec dbt-service bash -c "cd medical_warehouse && dbt test"

# 4. Check code style

docker-compose exec dbt-service black --check src/ api/ scripts/

docker-compose exec dbt-service flake8 src/ api/ scripts/

# 5. Commit and push

git commit -m "feat: add new product analysis endpoint"

git push origin feature/new-analysis

# 6. Create pull request

Code Standards:

Python: PEP 8, type hints, docstrings

SQL: CTEs, meaningful aliases, comments

Tests: pytest for Python, dbt tests for data

Documentation: Inline comments + API docs

📄 License & Attribution

This project is developed for Kara Solutions' Ethiopian medical market analysis.

Technology Stack:

Telethon: Telegram API client

dbt: Data transformation framework

FastAPI: Modern web API framework

Dagster: Data orchestration platform

YOLOv8: Computer vision model

PostgreSQL: Relational database

License: MIT - See LICENSE file for details.
