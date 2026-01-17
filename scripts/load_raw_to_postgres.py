import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PostgresLoader:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / 'data' / 'raw' / 'telegram_messages'
        self.logs_dir = self.base_dir / 'logs'
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Database connection
        self.engine = self._create_engine()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_file = self.logs_dir / f'postgres_loader_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def _create_engine(self):
        """Create SQLAlchemy engine"""
        db_user = os.getenv('POSTGRES_USER', 'medical_user')
        db_password = os.getenv('POSTGRES_PASSWORD', 'secure_password')
        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'medical_warehouse')
        
        connection_string = (
            f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )
        
        return create_engine(connection_string)
    
    def create_raw_schema(self):
        """Create raw schema and table if not exists"""
        create_schema_sql = """
        CREATE SCHEMA IF NOT EXISTS raw;
        
        CREATE TABLE IF NOT EXISTS raw.telegram_messages (
            id SERIAL PRIMARY KEY,
            message_id BIGINT,
            channel_name VARCHAR(255),
            message_date TIMESTAMP,
            message_text TEXT,
            has_media BOOLEAN,
            image_path VARCHAR(500),
            views INTEGER,
            forwards INTEGER,
            raw_data JSONB,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_file VARCHAR(500)
        );
        
        CREATE INDEX IF NOT EXISTS idx_channel_date ON raw.telegram_messages(channel_name, message_date);
        CREATE INDEX IF NOT EXISTS idx_raw_data ON raw.telegram_messages USING GIN(raw_data);
        """
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text(create_schema_sql))
                conn.commit()
            self.logger.info("Raw schema created successfully")
        except SQLAlchemyError as e:
            self.logger.error(f"Error creating schema: {e}")
            raise
    
    def find_json_files(self) -> List[Path]:
        """Find all JSON files in the data directory"""
        json_files = list(self.data_dir.rglob('*.json'))
        self.logger.info(f"Found {len(json_files)} JSON files")
        return json_files
    
    def process_json_file(self, file_path: Path) -> List[Dict]:
        """Process a single JSON file and extract messages"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = []
            for msg in data.get('messages', []):
                # Flatten the message data
                flattened_msg = {
                    'message_id': msg.get('message_id'),
                    'channel_name': msg.get('channel_name'),
                    'message_date': msg.get('message_date'),
                    'message_text': msg.get('message_text', '')[:10000],  # Limit text length
                    'has_media': msg.get('has_media', False),
                    'image_path': msg.get('image_path'),
                    'views': msg.get('views', 0),
                    'forwards': msg.get('forwards', 0),
                    'raw_data': json.dumps(msg.get('raw_data', {})),
                    'source_file': str(file_path.relative_to(self.base_dir))
                }
                messages.append(flattened_msg)
            
            self.logger.info(f"Processed {len(messages)} messages from {file_path.name}")
            return messages
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return []
    
    def load_to_postgres(self, messages: List[Dict]):
        """Load messages to PostgreSQL"""
        if not messages:
            return
        
        df = pd.DataFrame(messages)
        
        try:
            # Load to database
            df.to_sql(
                name='telegram_messages',
                schema='raw',
                con=self.engine,
                if_exists='append',
                index=False,
                dtype={
                    'raw_data': 'JSONB',
                    'message_text': 'TEXT'
                }
            )
            
            self.logger.info(f"Loaded {len(df)} messages to PostgreSQL")
            
        except SQLAlchemyError as e:
            self.logger.error(f"Error loading to PostgreSQL: {e}")
            raise
    
    def run(self):
        """Main execution method"""
        self.logger.info("Starting PostgreSQL data loader...")
        
        try:
            # Create schema
            self.create_raw_schema()
            
            # Find and process JSON files
            json_files = self.find_json_files()
            
            total_messages = 0
            for json_file in json_files:
                messages = self.process_json_file(json_file)
                if messages:
                    self.load_to_postgres(messages)
                    total_messages += len(messages)
            
            self.logger.info(f"Data loading completed. Total messages loaded: {total_messages}")
            
        except Exception as e:
            self.logger.error(f"Fatal error in data loader: {e}")
            raise

def main():
    """Main entry point"""
    loader = PostgresLoader()
    loader.run()

if __name__ == "__main__":
    main()