FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install dbt
RUN pip install dbt-postgres

# Copy project files
COPY . .

# Set Python path
ENV PYTHONPATH=/app

CMD ["python", "-m", "src.scraper"]