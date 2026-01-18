# Medical Telegram Data Warehouse

# A complete end-to-end data pipeline for scraping, storing, transforming, and analyzing Ethiopian medical Telegram channels.

📋 Table of Contents

Overview

Features

System Architecture

Prerequisites

Quick Start

Detailed Setup

Project Structure

Configuration

Usage Guide

Data Models

API Documentation

Testing

Monitoring & Logging

Troubleshooting

Deployment

Contributing

 License

📊 Overview

This project provides a comprehensive data engineering solution for collecting and analyzing medical product 

information from Ethiopian Telegram channels. It automates the entire data pipeline from extraction to presentation.

Use Cases

Market Research: Track pharmaceutical and medical product trends

Price Monitoring: Monitor pricing strategies across different channels

Product Analysis: Identify popular products and categories

Engagement Metrics: Analyze channel performance and user engagement

Regulatory Compliance: Monitor unregulated medical product sales

🎯 Features

Core Components

Telegram Scraper: Automated scraping using Telethon library

Data Lake: Raw JSON storage with partitioned directory structure

Image Storage: Automatic image download and organization

PostgreSQL: Relational database for structured storage

dbt Transformation: Modern data transformation with testing

Star Schema: Optimized dimensional model for analytics

FastAPI: RESTful API with automatic documentation

Docker: Containerized environment for easy deployment

CI/CD: GitHub Actions for automated testing

Advanced Features

Error Handling: Comprehensive logging and error recovery

Rate Limiting: Built-in protection against Telegram API limits

Data Validation: Automated data quality checks

Partitioned Storage: Efficient data organization by date

Surrogate Keys: Consistent dimension referencing

Custom Tests: Business logic validation in dbt

🏗️ System Architecture

text
┌─────────────────────────────────────────────────────────────┐
│                    DATA PIPELINE FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐       │
│  │            │    │            │    │            │       │
│  │  EXTRACT   │───▶│   LOAD     │───▶│ TRANSFORM  │       │
│  │            │    │            │    │            │       │
│  └────────────┘    └────────────┘    └────────────┘       │
│       │                    │                    │           │
│  Telegram API        PostgreSQL          dbt Models        │
│  JSON + Images      Raw Schema        Star Schema          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                      ┌───────────────┐
                      │               │
                      │     API       │
                      │               │
                      └───────────────┘
                              │
                      ┌───────────────┐
                      │               │
                      │   Analytics   │
                      │    & BI       │
                      │               │
                      └───────────────┘

📋 Prerequisites

Required Software

Docker 20.10+ and Docker Compose 2.0+

Python 3.10+ (for local development)

Git for version control

Telegram Account with verified phone number

Telegram API Setup

Visit my.telegram.org

Log in with your phone number (including country code)

Click "API Development Tools"

Create a new application:

App title: MedicalDataScraper

Short name: med-scraper

Platform: Web

Description: Data collection for medical product analysis

Save your api_id and api_hash

Storage Requirements

Minimum 10GB free disk space for data storage

4GB RAM for Docker containers

Stable internet connection for Telegram API access

🚀 Quick Start

1. Clone and Setup

bash

# Clone the repository

git clone https://github.com/Saronzeleke/Medical-telegram-warehouse-week8.git

cd medical-telegram-warehouse

# Create environment file

cp .env.example .env

# Edit .env with your credentials

nano .env  # or use your preferred editor

2. Configure Environment

bash

# .env file content

TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE=+251XXXXXXXXX
POSTGRES_USER=medical_user
POSTGRES_PASSWORD=yoursecurepassword
POSTGRES_DB=medical_warehouse
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

3. Start Services
bash

# Build and start all containers

docker-compose up --build -d

# Verify services are running

docker-compose ps

# Expected output:

# NAME                          STATUS              PORTS

# medical-telegram-warehouse-fastapi-1   running   0.0.0.0:8000->8000/tcp

# medical-telegram-warehouse-postgres-1  running   0.0.0.0:5432->5432/tcp

# medical-telegram-warehouse-dbt-service-1 running   (health)

4. Run the Pipeline

bash

# Step 1: Scrape Telegram data

docker-compose exec dbt-service python -m src.scraper

# Step 2: Load to PostgreSQL

docker-compose exec dbt-service python scripts/load_raw_to_postgres.py

# Step 3: Transform with dbt

docker-compose exec dbt-service bash

cd medical_warehouse

dbt run

dbt test

# Step 4: Access the API

# Open browser: http://localhost:8000/docs

📁 Detailed Setup

Telegram API Credentials

bash

# Get your credentials from:

# https://my.telegram.org/auth

# Format for Ethiopia:

TELEGRAM_PHONE=+251911234567  # Country code +251, then 9-digit number

Manual Installation (Without Docker)

bash

# 1. Create virtual environment

python -m venv venv

source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies

pip install -r requirements.txt

pip install dbt-postgres

# 3. Start PostgreSQL manually

# Install PostgreSQL 14+ and create database

# 4. Configure dbt

cd medical_warehouse

cp profiles.example.yml profiles.yml

# Edit profiles.yml with your database credentials

# 5. Run the pipeline

python -m src.scraper

python scripts/load_raw_to_postgres.py

dbt run

Database Initialization

sql

-- Manual database setup (if not using Docker)

CREATE DATABASE medical_warehouse;

CREATE USER medical_user WITH PASSWORD 'secure_password_123';

GRANT ALL PRIVILEGES ON DATABASE medical_warehouse TO medical_user;

📂 Project Structure

text

medical-telegram-warehouse/

├── .github/workflows/          # CI/CD pipelines

├── .vscode/                    # IDE settings

├── api/                        # FastAPI application

│   ├── main.py                 # API endpoints

│   ├── database.py             # Database connection

│   ├── schemas.py              # Pydantic models

│   └── crud.py                 # Database operations

├── data/                       # Data storage

│   └── raw/

│       ├── telegram_messages/  # Partitioned JSON files

│       │   └── YYYY-MM-DD/

│       │       └── channel_name.json

│       └── images/             # Downloaded images

│           └── channel_name/

│               └── message_id.jpg

├── logs/                       # Application logs

│   ├── scraper_YYYYMMDD.log

│   ├── postgres_loader_YYYYMMDD.log

│   └── api.log

├── medical_warehouse/          # dbt project

│   ├── models/

│   │   ├── staging/            # Cleaning models

│   │   │   ├── stg_telegram_messages.sql

│   │   │   └── schema.yml

│   │   └── marts/              # Star schema

│   │       ├── dim_channels.sql

│   │       ├── dim_dates.sql

│   │       ├── fct_messages.sql

│   │       └── schema.yml

│   ├── tests/                  # Custom tests

│   │   ├── assert_no_future_messages.sql

│   │   └── assert_positive_views.sql

│   ├── dbt_project.yml         # dbt configuration

│   └── profiles.yml            # Database profiles

├── notebooks/                  # Jupyter notebooks

├── scripts/                    # Utility scripts

│   └── load_raw_to_postgres.py

├── src/                        # Source code

│   └── scraper.py              # Telegram scraper

├── tests/                      # Unit tests

├── .env                        # Environment variables

├── .gitignore                  # Git ignore rules

├── docker-compose.yml          # Docker orchestration

├── Dockerfile                  # Docker image

├── requirements.txt            # Python dependencies

└── README.md                   # This file

⚙️ Configuration

Telegram Channels Configuration

Edit src/scraper.py to modify channels:

python

# Add more channels

self.channels = {
    'chemed': 'chemed_username',           # Medical products
    'lobelia_cosmetics': 'lobelia4cosmetics',  # Cosmetics
    'tikvah_pharma': 'tikvahpharma',       # Pharmaceuticals
    # Add more channels from et.tgstat.com
    'ethio_pharma': 'ethiopharmachannel',
    'addis_medical': 'addismedicalsupplies'
}
Scraping Parameters

python

# Adjust in scraper.py

DAYS_BACK = 30        # How many days to scrape

BATCH_SIZE = 100      # Messages per API call

DELAY_BETWEEN_CALLS = 2  # Seconds between API calls

MAX_MESSAGES = 10000  # Safety limit per channel

dbt Configuration

yaml

# medical_warehouse/dbt_project.yml

models:
  medical_warehouse:
    staging:
      +schema: staging
      +materialized: view    # Views for staging
    marts:
      +schema: marts
      +materialized: table   # Tables for marts

📖 Usage Guide

Running the Scraper

bash

# Basic scraping (default:)

docker-compose exec dbt-service python -m src.scraper

# Scrape specific date range

docker-compose exec dbt-service python -c "
from src.scraper import TelegramScraper
import asyncio

async def run():
    scraper = TelegramScraper()
    client = await scraper.initialize_client()
    # Scrape custom range
    await scraper.scrape_channel(client, 'tikvahpharma', 'tikvah_pharma', days_back=60)

asyncio.run(run())
"

# Check scraping logs

tail -f logs/scraper_$(date +%Y%m%d).log

Loading Data to PostgreSQL
bash

# Load all JSON files

docker-compose exec dbt-service python scripts/load_raw_to_postgres.py

# Load specific date range

docker-compose exec dbt-service python -c "
from scripts.load_raw_to_postgres import PostgresLoader
loader = PostgresLoader()

# Custom logic for specific dates
"

# Verify loaded data

docker-compose exec postgres psql -U medical_user -d medical_warehouse -c "
SELECT 
    channel_name,
    COUNT(*) as message_count,
    MIN(message_date) as earliest,
    MAX(message_date) as latest
FROM raw.telegram_messages 
GROUP BY channel_name;
"
dbt Operations

bash

# Enter dbt container

docker-compose exec dbt-service bash

# Common dbt commands

cd medical_warehouse

# Run specific models

dbt run --select staging           # Only staging models

dbt run --select marts             # Only mart models

dbt run --select dim_channels      # Specific model

dbt run --select +fct_messages     # Model and dependencies

# Run tests

dbt test                           # All tests

dbt test --select test_type:singular  # Custom tests

dbt test --select tag:staging      # Staging model tests

# Generate documentation

dbt docs generate

dbt docs serve --port 8081        # Different port if 8080 is busy

# Debug connection

dbt debug

# List models

dbt ls

dbt ls --resource-type model

API Usage Examples

bash

# Using curl

curl "http://localhost:8000/channels"

curl "http://localhost:8000/messages?channel_name=tikvah_pharma&limit=10"

curl "http://localhost:8000/stats/daily?start_date=2024-01-01"

# Using Python

import requests

response = requests.get("http://localhost:8000/channels")

channels = response.json()

# Search for specific products

response = requests.get(
    "http://localhost:8000/search",
    params={"query": "antibiotic", "limit": 20}
)
Sample Queries for Analysis
sql
-- Top 10 most viewed messages
SELECT 
    dc.channel_name,
    fm.message_text,
    fm.view_count,
    fm.forward_count,
    dd.full_date
FROM marts.fct_messages fm
JOIN marts.dim_channels dc ON fm.channel_key = dc.channel_key
JOIN marts.dim_dates dd ON fm.date_key = dd.date_key
ORDER BY fm.view_count DESC
LIMIT 10;

-- Daily activity summary
SELECT 
    dd.full_date,
    COUNT(*) as message_count,
    SUM(fm.view_count) as total_views,
    AVG(fm.view_count) as avg_views,
    COUNT(CASE WHEN fm.has_image THEN 1 END) as messages_with_images
FROM marts.fct_messages fm
JOIN marts.dim_dates dd ON fm.date_key = dd.date_key
GROUP BY dd.full_date
ORDER BY dd.full_date DESC;

-- Channel performance comparison
SELECT 
    channel_name,
    channel_type,
    total_posts,
    total_views,
    ROUND(total_views::decimal / NULLIF(total_posts, 0), 2) as views_per_post,
    activity_level,
    ROUND(avg_views, 2) as avg_views_per_message
FROM marts.dim_channels
ORDER BY total_views DESC;

🗃️ Data Models

Star Schema Design

text

┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│  dim_channels   │◄────┤   fct_messages   ├─────►│   dim_dates     │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
      PK: channel_key           PK: message_id          PK: date_key
      • channel_name            • channel_key (FK)     • full_date
      • channel_type            • date_key (FK)        • year, month
      • first_post_date         • message_text         • quarter
      • last_post_date          • message_length       • week_of_year
      • total_posts             • view_count           • day_of_week
      • avg_views               • forward_count        • is_weekend
      • activity_level          • has_image
                                • forward_rate
Table Descriptions

dim_channels

Information about each Telegram channel with activity statistics.

dim_dates

Date dimension table for time-based analysis with pre-calculated attributes.

fct_messages

Fact table containing individual message metrics and engagement data.

🔌 API Documentation

The FastAPI provides automatic OpenAPI documentation at http://localhost:8000/docs.

Key Endpoints

Endpoint	Method	Description	Parameters

/channels	GET	List all channels	skip, limit, channel_type

/channels/{name}	GET	Channel details	-

/messages	GET	Get messages	channel_name, start_date, end_date, has_image

/stats/daily	GET	Daily statistics	start_date, end_date

/stats/channels	GET	Channel statistics	days

/search	GET	Search messages	query, limit

Example API Calls

python

import requests
from datetime import date, timedelta

# Get channels with filtering

channels = requests.get(
    "http://localhost:8000/channels",
    params={"channel_type": "Pharmaceutical", "limit": 50}
).json()

# Get messages from last week

last_week = date.today() - timedelta(days=7)
messages = requests.get(
    "http://localhost:8000/messages",
    params={
        "start_date": last_week,
        "has_image": True,
        "limit": 100
    }
).json()

# Search for specific products

search_results = requests.get(
    "http://localhost:8000/search",
    params={"query": "painkiller OR antibiotic", "limit": 30}
).json()

🧪 Testing

Running Tests

bash

# Run all tests

docker-compose exec dbt-service pytest tests/

# Run specific test file

docker-compose exec dbt-service pytest tests/test_scraper.py

# Run with coverage

docker-compose exec dbt-service pytest --cov=src --cov-report=html

# dbt tests

docker-compose exec dbt-service bash

cd medical_warehouse

dbt test

Test Types

Unit Tests: Python code testing

dbt Tests: Data quality tests

Unique constraints

Not null constraints

Referential integrity

Custom business rules

Integration Tests: End-to-end pipeline testing

Custom dbt Tests

sql
-- tests/assert_no_future_messages.sql
-- Ensures no messages have future dates

-- tests/assert_positive_views.sql
-- Ensures view counts are non-negative

-- tests/assert_valid_message_length.sql
-- Ensures message text has reasonable length

📊 Monitoring & Logging

Log Files

logs/scraper_YYYYMMDD.log - Scraping activities and errors

logs/postgres_loader_YYYYMMDD.log - Data loading logs

logs/api_YYYYMMDD.log - API request logs

Monitoring Queries

sql

-- System health check
SELECT 
    schema_name,
    table_name,
    pg_size_pretty(pg_total_relation_size('"'||schema_name||'"."'||table_name||'"')) as size
FROM information_schema.tables 
WHERE table_schema IN ('raw', 'staging', 'marts')
ORDER BY pg_total_relation_size('"'||schema_name||'"."'||table_name||'"') DESC;

-- Data freshness
SELECT 
    channel_name,
    MAX(message_date) as latest_message,
    CURRENT_DATE - MAX(message_date::date) as days_since_last_message
FROM staging.stg_telegram_messages
GROUP BY channel_name;

🔧 Troubleshooting

Common Issues

Telegram API Authentication Failed

bash

# Check credentials

echo "API_ID: $TELEGRAM_API_ID"

echo "API_HASH: $TELEGRAM_API_HASH"

# Test authentication manually

docker-compose exec dbt-service python -c "
from telethon import TelegramClient
import asyncio
import os

async def test():
    3client = TelegramClient(
        'test_session',
        int(os.getenv('TELEGRAM_API_ID')),
        os.getenv('TELEGRAM_API_HASH')
    )
    await client.start(os.getenv('TELEGRAM_PHONE'))
    print('Authentication successful')
    await client.disconnect()

asyncio.run(test())
"
Database Connection Issues

bash

# Test PostgreSQL connection

docker-compose exec postgres pg_isready

# Check logs

docker-compose logs postgres

# Reset database (warning: deletes data)

docker-compose down -v

docker-compose up -d

dbt Connection Errors

bash

# Debug dbt connection

docker-compose exec dbt-service bash

cd medical_warehouse

dbt debug

# Check profiles.yml

cat profiles.yml

# Test direct connection

psql "postgresql://medical_user:secure_password_123@postgres:5432/medical_warehouse"

Rate Limiting from Telegram

bash

# Symptoms: Frequent timeouts or authentication errors

# Solution: Increase delays in scraper.py

# Current settings in scraper.py

DELAY_BETWEEN_CHANNELS = 5  # seconds

DELAY_BETWEEN_REQUESTS = 2  # seconds

# Increase if needed

DELAY_BETWEEN_CHANNELS = 10

DELAY_BETWEEN_REQUESTS = 5

Disk Space Issues

bash

# Check disk usage

docker system df

# Clean up old images

docker system prune -a

# Clean data directories

rm -rf data/raw/telegram_messages/*/  # Keep structure, remove data

Performance Optimization

Increase Database Performance

sql

-- Add indexes for common queries
CREATE INDEX idx_fct_messages_date_channel 
ON marts.fct_messages(date_key, channel_key);

CREATE INDEX idx_fct_messages_views 
ON marts.fct_messages(view_count DESC);

-- Vacuum and analyze regularly
VACUUM ANALYZE raw.telegram_messages;
VACUUM ANALYZE marts.fct_messages;
Optimize Scraping

python

# Adjust batch size in scraper.py

BATCH_SIZE = 200  # More messages per request

DAYS_BACK = 7     # Scrape only recent data for routine runs

🚢 Deployment

Production Deployment

bash

# 1. Create production .env

cp .env .env.production

# Update with production credentials

# 2. Use production docker-compose

docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. Schedule scraping with cron

# Add to crontab (scrape daily at 2 AM)

0 2 * * * cd /path/to/project && docker-compose exec dbt-service python -m src.scraper >> /var/log/telegram_scraper.log 
2>&1

Docker Compose Production Override

yaml

# docker-compose.prod.yml

version: '3.8'

services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    
  fastapi:
    restart: unless-stopped
    ports:
      - "80:8000"
    
  dbt-service:
    restart: unless-stopped
    command: ["sleep", "infinity"]

Backup Strategy

# Backup database

docker-compose exec postgres pg_dump -U medical_user medical_warehouse > backup_$(date +%Y%m%d).sql

# Backup data files

tar -czf data_backup_$(date +%Y%m%d).tar.gz data/raw/

# Restore database

docker-compose exec -T postgres psql -U medical_user medical_warehouse < backup_file.sql

🤝 Contributing

Development Workflow

Fork the repository

Create a feature branch

Make changes with tests

Run all tests

Submit pull request

Code Standards

Follow PEP 8 for Python code

Use meaningful variable names

Add docstrings to functions

Include tests for new features

Update documentation

Testing Before PR

# Run full test suite

docker-compose exec dbt-service pytest tests/ --cov=src --cov-report=html

docker-compose exec dbt-service bash -c "cd medical_warehouse && dbt test"

# Check code style

docker-compose exec dbt-service flake8 src/ api/ scripts/

docker-compose exec dbt-service black --check src/ api/ scripts/

📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments

Telegram for providing the API

dbt Labs for the data transformation framework

FastAPI for the modern web framework

Docker for containerization

📞 Support

For issues and questions:

Check the Troubleshooting section

Review existing GitHub issues

Create a new issue with detailed description

