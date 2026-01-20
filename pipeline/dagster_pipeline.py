import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dagster import (
    Definitions,
    JobDefinition,
    OpExecutionContext,
    job,
    op,
    schedule,
    ScheduleDefinition,
    Failure,
    RetryPolicy,
    ResourceDefinition,
    StringSource,
    Field
)
from dagster_dbt import DbtCliResource, dbt_assets
from dagster_aws.s3 import S3Resource
from dagster_docker import DockerRunLauncher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Resource definitions
@resource(config_schema={
    "telegram_api_id": Field(StringSource, description="Telegram API ID"),
    "telegram_api_hash": Field(StringSource, description="Telegram API Hash"),
    "telegram_phone": Field(StringSource, description="Telegram phone number"),
    "postgres_host": Field(StringSource, description="PostgreSQL host"),
    "postgres_port": Field(StringSource, description="PostgreSQL port", default_value="5432"),
    "postgres_db": Field(StringSource, description="PostgreSQL database"),
    "postgres_user": Field(StringSource, description="PostgreSQL user"),
    "postgres_password": Field(StringSource, description="PostgreSQL password"),
})
def pipeline_resources(context):
    """Resource provider for pipeline configuration"""
    return {
        "telegram": {
            "api_id": context.resource_config["telegram_api_id"],
            "api_hash": context.resource_config["telegram_api_hash"],
            "phone": context.resource_config["telegram_phone"],
        },
        "postgres": {
            "host": context.resource_config["postgres_host"],
            "port": context.resource_config["postgres_port"],
            "db": context.resource_config["postgres_db"],
            "user": context.resource_config["postgres_user"],
            "password": context.resource_config["postgres_password"],
        }
    }

# Operations
@op(
    required_resource_keys={"resources"},
    tags={"component": "scraping", "cost": "low"},
    retry_policy=RetryPolicy(max_retries=2, delay=300)  # 5 min delay between retries
)
def scrape_telegram_data(context: OpExecutionContext):
    """Scrape data from Telegram channels"""
    try:
        logger.info("Starting Telegram data scraping...")
        
        # Import here to avoid dependencies at module level
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        
        from src.scraper import TelegramScraper
        import asyncio
        
        # Initialize and run scraper
        scraper = TelegramScraper()
        
        # Run in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(scraper.run())
            logger.info(f"Scraping completed. Messages collected: {result}")
            
            # Check if scraping was successful
            scraped_dir = Path("data/raw/telegram_messages")
            today_dir = scraped_dir / datetime.now().strftime("%Y-%m-%d")
            
            if today_dir.exists():
                json_files = list(today_dir.glob("*.json"))
                context.log.info(f"Created {len(json_files)} JSON files in {today_dir}")
                
                # Yield asset materialization
                yield AssetMaterialization(
                    asset_key="telegram_raw_data",
                    description=f"Scraped data from Telegram channels",
                    metadata={
                        "json_files": len(json_files),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "channels": ["chemed", "lobelia_cosmetics", "tikvah_pharma"]
                    }
                )
                
                return {
                    "status": "success",
                    "files_created": len(json_files),
                    "date": datetime.now().strftime("%Y-%m-%d")
                }
            else:
                raise Failure("No data files created during scraping")
                
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise Failure(f"Telegram scraping failed: {str(e)}")

@op(
    required_resource_keys={"resources"},
    tags={"component": "loading", "cost": "medium"},
    retry_policy=RetryPolicy(max_retries=3, delay=60)
)
def load_raw_to_postgres(context: OpExecutionContext, scrape_result: dict):
    """Load scraped JSON data to PostgreSQL"""
    try:
        logger.info("Loading raw data to PostgreSQL...")
        
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        
        from scripts.load_raw_to_postgres import PostgresLoader
        
        loader = PostgresLoader()
        loader.run()
        
        # Check database
        import psycopg2
        from psycopg2 import sql
        
        conn = psycopg2.connect(
            host=context.resources.resources["postgres"]["host"],
            port=context.resources.resources["postgres"]["port"],
            dbname=context.resources.resources["postgres"]["db"],
            user=context.resources.resources["postgres"]["user"],
            password=context.resources.resources["postgres"]["password"]
        )
        
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM raw.telegram_messages")
            count = cur.fetchone()[0]
        
        conn.close()
        
        context.log.info(f"Loaded {count} total messages to PostgreSQL")
        
        yield AssetMaterialization(
            asset_key="postgres_raw_data",
            description="Raw data loaded to PostgreSQL",
            metadata={
                "table": "raw.telegram_messages",
                "row_count": count,
                "database": context.resources.resources["postgres"]["db"]
            }
        )
        
        return {
            "status": "success",
            "rows_loaded": count,
            "table": "raw.telegram_messages"
        }
        
    except Exception as e:
        logger.error(f"Database loading failed: {e}")
        raise Failure(f"PostgreSQL loading failed: {str(e)}")

@op(
    required_resource_keys={"dbt"},
    tags={"component": "transformation", "cost": "high"},
    retry_policy=RetryPolicy(max_retries=2, delay=120)
)
def run_dbt_transformations(context: OpExecutionContext, load_result: dict):
    """Run dbt transformations to create star schema"""
    try:
        logger.info("Running dbt transformations...")
        
        # Change to dbt project directory
        dbt_project_dir = Path(__file__).parent.parent / "medical_warehouse"
        
        # Run dbt commands
        context.resources.dbt.run()
        
        # Run tests
        test_results = context.resources.dbt.test()
        
        # Check for test failures
        failures = [r for r in test_results if r.status != "pass"]
        
        if failures:
            failure_details = "\n".join([f"{f.node.name}: {f.status}" for f in failures])
            raise Failure(f"dbt tests failed:\n{failure_details}")
        
        # Get model information
        dbt_docs = context.resources.dbt.docs_generate()
        
        context.log.info("dbt transformations completed successfully")
        
        yield AssetMaterialization(
            asset_key="dbt_models",
            description="dbt models transformed and tested",
            metadata={
                "models_created": ["dim_channels", "dim_dates", "fct_messages"],
                "tests_passed": len(test_results) - len(failures),
                "tests_failed": len(failures)
            }
        )
        
        return {
            "status": "success",
            "models_built": ["dim_channels", "dim_dates", "fct_messages"],
            "tests_passed": len(test_results) - len(failures)
        }
        
    except Exception as e:
        logger.error(f"dbt transformation failed: {e}")
        raise Failure(f"dbt transformation failed: {str(e)}")

@op(
    required_resource_keys={"resources"},
    tags={"component": "enrichment", "cost": "high"},
    retry_policy=RetryPolicy(max_retries=2, delay=180)
)
def run_yolo_enrichment(context: OpExecutionContext, dbt_result: dict):
    """Run YOLO object detection on downloaded images"""
    try:
        logger.info("Running YOLO image enrichment...")
        
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        
        from src.yolo_detect import YOLODetector
        
        detector = YOLODetector()
        results = detector.run()
        
        if results:
            # Load results to database
            detector.load_to_postgres(results)
            
            # Analyze results
            categories = [r['image_category'] for r in results]
            from collections import Counter
            category_counts = Counter(categories)
            
            context.log.info(f"YOLO enrichment completed: {len(results)} images analyzed")
            context.log.info(f"Category distribution: {dict(category_counts)}")
            
            yield AssetMaterialization(
                asset_key="yolo_detections",
                description="YOLO object detection results",
                metadata={
                    "images_analyzed": len(results),
                    "categories": dict(category_counts),
                    "table": "raw.yolo_detections"
                }
            )
            
            # Run dbt for image detections
            dbt_project_dir = Path(__file__).parent.parent / "medical_warehouse"
            os.chdir(dbt_project_dir)
            
            import subprocess
            subprocess.run(["dbt", "run", "--select", "fct_image_detections"], check=True)
            
            return {
                "status": "success",
                "images_analyzed": len(results),
                "categories": dict(category_counts)
            }
        else:
            logger.warning("No images found for YOLO processing")
            return {
                "status": "skipped",
                "reason": "No images found"
            }
        
    except Exception as e:
        logger.error(f"YOLO enrichment failed: {e}")
        raise Failure(f"YOLO enrichment failed: {str(e)}")

@op(
    tags={"component": "api", "cost": "low"},
    retry_policy=RetryPolicy(max_retries=1, delay=30)
)
def refresh_api_cache(context: OpExecutionContext, enrichment_result: dict):
    """Refresh API cache after pipeline completion"""
    try:
        logger.info("Refreshing API cache...")
        
        # In a production environment, this would:
        # 1. Clear cache for analytical endpoints
        # 2. Precompute common queries
        # 3. Update materialized views
        
        # For now, just log and simulate
        context.log.info("API cache refresh initiated")
        
        # Simulate cache refresh delay
        import time
        time.sleep(2)
        
        yield AssetMaterialization(
            asset_key="api_cache",
            description="API cache refreshed",
            metadata={
                "timestamp": datetime.now().isoformat(),
                "pipeline_completed": True
            }
        )
        
        return {
            "status": "success",
            "cache_refreshed": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache refresh failed: {e}")
        # Don't fail the whole pipeline for cache refresh
        context.log.warning(f"Cache refresh failed but pipeline continues: {e}")
        return {
            "status": "failed",
            "error": str(e)
        }

@op(
    tags={"component": "monitoring", "cost": "low"}
)
def send_pipeline_notification(context: OpExecutionContext, cache_result: dict, 
                             scrape_result: dict, load_result: dict, 
                             dbt_result: dict, enrichment_result: dict):
    """Send notification about pipeline completion"""
    try:
        # Calculate pipeline statistics
        total_messages = load_result.get("rows_loaded", 0)
        images_analyzed = enrichment_result.get("images_analyzed", 0)
        
        # Check for failures
        failures = []
        if scrape_result.get("status") != "success":
            failures.append("scraping")
        if load_result.get("status") != "success":
            failures.append("loading")
        if dbt_result.get("status") != "success":
            failures.append("dbt")
        if enrichment_result.get("status") not in ["success", "skipped"]:
            failures.append("enrichment")
        
        # Prepare notification message
        if failures:
            message = f"Pipeline completed with failures in: {', '.join(failures)}"
            severity = "ERROR"
        else:
            message = f"Pipeline completed successfully. Processed {total_messages} messages"
            if images_analyzed > 0:
                message += f" and analyzed {images_analyzed} images"
            severity = "INFO"
        
        # Log notification
        context.log.info(f"Pipeline notification: {message}")
        
        # In production, send actual notifications (Slack, Email, etc.)
        # For now, just log and create asset
        
        yield AssetMaterialization(
            asset_key="pipeline_notification",
            description="Pipeline completion notification",
            metadata={
                "message": message,
                "severity": severity,
                "total_messages": total_messages,
                "images_analyzed": images_analyzed,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Also create a pipeline summary
        summary = {
            "pipeline_run_id": context.run_id,
            "timestamp": datetime.now().isoformat(),
            "status": "failed" if failures else "success",
            "failures": failures,
            "statistics": {
                "messages_processed": total_messages,
                "images_analyzed": images_analyzed,
                "dbt_tests_passed": dbt_result.get("tests_passed", 0)
            },
            "components": {
                "scraping": scrape_result.get("status"),
                "loading": load_result.get("status"),
                "dbt": dbt_result.get("status"),
                "enrichment": enrichment_result.get("status"),
                "api_cache": cache_result.get("status")
            }
        }
        
        # Save summary to file
        summary_dir = Path("data/processed/pipeline_summaries")
        summary_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        summary_file = summary_dir / f"run_{context.run_id}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        context.log.info(f"Pipeline summary saved to {summary_file}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Notification failed: {e}")
        # Don't fail pipeline for notification errors
        return {
            "status": "notification_failed",
            "error": str(e)
        }

# Define the complete pipeline job
@job(
    resource_defs={
        "resources": pipeline_resources,
        "dbt": DbtCliResource(project_dir=Path(__file__).parent.parent / "medical_warehouse")
    },
    config={
        "ops": {
            "scrape_telegram_data": {
                "config": {
                    "max_channels": 3,
                    "days_back": 7
                }
            },
            "run_yolo_enrichment": {
                "config": {
                    "max_images": 100
                }
            }
        }
    },
    tags={
        "pipeline": "medical_telegram",
        "team": "data_engineering",
        "environment": "production"
    }
)
def medical_telegram_pipeline():
    """Complete medical Telegram data pipeline"""
    
    # Execute pipeline steps in order
    scrape_result = scrape_telegram_data()
    load_result = load_raw_to_postgres(scrape_result)
    dbt_result = run_dbt_transformations(load_result)
    enrichment_result = run_yolo_enrichment(dbt_result)
    cache_result = refresh_api_cache(enrichment_result)
    
    # Send final notification
    pipeline_summary = send_pipeline_notification(
        cache_result, scrape_result, load_result, 
        dbt_result, enrichment_result
    )
    
    return pipeline_summary

# Schedules
@schedule(
    job=medical_telegram_pipeline,
    cron_schedule="0 2 * * *",  # Daily at 2 AM
    execution_timezone="Africa/Addis_Ababa"
)
def daily_pipeline_schedule(context):
    """Daily pipeline execution schedule"""
    run_date = context.scheduled_execution_time.strftime("%Y-%m-%d")
    
    return {
        "ops": {
            "scrape_telegram_data": {
                "config": {
                    "days_back": 1,  # Only scrape yesterday's data for daily runs
                    "run_date": run_date
                }
            }
        }
    }

@schedule(
    job=medical_telegram_pipeline,
    cron_schedule="0 0 * * 0",  # Weekly on Sunday at midnight
    execution_timezone="Africa/Addis_Ababa"
)
def weekly_full_pipeline_schedule(context):
    """Weekly full pipeline execution"""
    return {
        "ops": {
            "scrape_telegram_data": {
                "config": {
                    "days_back": 7,  # Full week for weekly run
                    "full_refresh": True
                }
            },
            "run_yolo_enrichment": {
                "config": {
                    "max_images": None  # No limit for weekly run
                }
            }
        }
    }

# Sensor for file-based triggering (optional)
@sensor(job=medical_telegram_pipeline)
def new_data_sensor(context):
    """Trigger pipeline when new data files appear"""
    data_dir = Path("data/raw/telegram_messages")
    
    # Check for new files since last run
    cursor = context.cursor or "1970-01-01"
    
    new_files = []
    for date_dir in data_dir.glob("*"):
        if date_dir.is_dir() and date_dir.name > cursor:
            json_files = list(date_dir.glob("*.json"))
            new_files.extend(json_files)
    
    if new_files:
        # Update cursor to latest date
        latest_date = max([f.parent.name for f in new_files])
        
        yield RunRequest(
            run_key=f"new_data_{latest_date}",
            run_config={
                "ops": {
                    "scrape_telegram_data": {
                        "config": {
                            "skip_scraping": True,  # Data already exists
                            "process_existing": True
                        }
                    }
                }
            },
            tags={"trigger": "new_data_sensor", "date": latest_date}
        )
        
        context.update_cursor(latest_date)

# Define all assets
@dbt_assets(manifest=Path(__file__).parent.parent / "medical_warehouse" / "target" / "manifest.json")
def dbt_medical_assets(context, dbt: DbtCliResource):
    """dbt assets for the medical warehouse"""
    yield from dbt.cli(["run"], context=context).stream()

# Pipeline definitions
defs = Definitions(
    jobs=[medical_telegram_pipeline],
    schedules=[daily_pipeline_schedule, weekly_full_pipeline_schedule],
    sensors=[new_data_sensor],
    assets=[dbt_medical_assets],
    resources={
        "resources": pipeline_resources,
        "dbt": DbtCliResource(project_dir=Path(__file__).parent.parent / "medical_warehouse")
    }
)

# Simple runner script
if __name__ == "__main__":
    """Command-line interface for the pipeline"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Medical Telegram Pipeline CLI")
    parser.add_argument("--run", action="store_true", help="Run the pipeline")
    parser.add_argument("--schedule", choices=["daily", "weekly"], help="Run scheduled pipeline")
    parser.add_argument("--test", action="store_true", help="Run test pipeline")
    
    args = parser.parse_args()
    
    if args.run:
        # Execute pipeline directly
        print("Running medical Telegram pipeline...")
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Create execution context
        from dagster import execute_job, reconstructable
        
        job_def = reconstructable(medical_telegram_pipeline)
        result = execute_job(job_def)
        
        if result.success:
            print("Pipeline completed successfully!")
        else:
            print(f"Pipeline failed: {result}")
            
    elif args.schedule:
        print(f"Running {args.schedule} schedule...")
        # Schedule execution would be handled by Dagster Daemon
        
    elif args.test:
        print("Running test mode...")
        # Run with limited data
        from dagster import execute_job, reconstructable
        
        job_def = reconstructable(medical_telegram_pipeline)
        result = execute_job(
            job_def,
            run_config={
                "ops": {
                    "scrape_telegram_data": {
                        "config": {"days_back": 1, "test_mode": True}
                    },
                    "run_yolo_enrichment": {
                        "config": {"max_images": 10}
                    }
                }
            }
        )
        
        print(f"Test result: {result.success}")
        
    else:
        print("Starting Dagster webserver...")
        # Start Dagster UI
        import subprocess
        subprocess.run(["dagster", "dev", "-f", __file__])