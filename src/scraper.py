#!/usr/bin/env python3
"""
Telegram Medical Channels Scraper
Scrapes Ethiopian medical Telegram channels and stores data
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Message, MessageMediaPhoto
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class TelegramMessage:
    """Data class for Telegram message"""
    message_id: int
    channel_name: str
    message_date: str
    message_text: str
    has_media: bool
    image_path: Optional[str]
    views: int
    forwards: int
    raw_data: Dict
    
class TelegramScraper:
    def __init__(self):
        # Setup paths
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / 'data' / 'raw'
        self.images_dir = self.data_dir / 'images'
        self.logs_dir = self.base_dir / 'logs'
        
        # Create directories
        self._create_directories()
        
        # Setup logging
        self._setup_logging()
        
        # Telegram channels to scrape
        self.channels = {
            'chemed': 'chemed',  # Update with actual username
            'lobelia_cosmetics': 'lobelia4cosmetics',
            'tikvah_pharma': 'tikvahpharma'
        }
        
        # Additional channels from et.tgstat.com (if accessible)
        self.additional_channels = []
        
        self.logger = logging.getLogger(__name__)
    
    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.data_dir / 'telegram_messages',
            self.images_dir,
            self.logs_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_file = self.logs_dir / f'scraper_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    async def initialize_client(self) -> TelegramClient:
        """Initialize Telegram client"""
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        phone = os.getenv('TELEGRAM_PHONE')
        
        if not all([api_id, api_hash, phone]):
            raise ValueError("Missing Telegram API credentials in .env file")
        
        client = TelegramClient(
            session='medical_scraper_session',
            api_id=int(api_id),
            api_hash=api_hash
        )
        
        await client.start(phone=phone)
        return client
    
    def _extract_message_data(self, message: Message, channel_name: str) -> TelegramMessage:
        """Extract relevant data from Telegram message"""
        # Check if message has media
        has_media = hasattr(message, 'media') and message.media is not None
        image_path = None
        
        # Extract views and forwards
        views = getattr(message, 'views', 0) or 0
        forwards = getattr(message, 'forwards', 0) or 0
        
        # Extract text
        message_text = message.message or ''
        
        return TelegramMessage(
            message_id=message.id,
            channel_name=channel_name,
            message_date=message.date.isoformat() if message.date else datetime.now().isoformat(),
            message_text=message_text,
            has_media=has_media,
            image_path=image_path,
            views=views,
            forwards=forwards,
            raw_data={
                'id': message.id,
                'date': message.date.isoformat() if message.date else None,
                'text': message_text,
                'media': str(message.media) if has_media else None,
                'views': views,
                'forwards': forwards,
                'reply_to_msg_id': getattr(message, 'reply_to_msg_id', None)
            }
        )
    
    async def download_image(self, client: TelegramClient, message: Message, 
                           channel_name: str) -> Optional[str]:
        """Download image from message if present"""
        if not hasattr(message, 'media') or not message.media:
            return None
        
        try:
            if isinstance(message.media, MessageMediaPhoto):
                # Create channel directory
                channel_image_dir = self.images_dir / channel_name
                channel_image_dir.mkdir(exist_ok=True)
                
                # Define image path
                image_path = channel_image_dir / f"{message.id}.jpg"
                
                # Download image
                await client.download_media(
                    message.media,
                    file=str(image_path)
                )
                
                self.logger.info(f"Downloaded image for message {message.id}")
                return str(image_path.relative_to(self.base_dir))
        
        except Exception as e:
            self.logger.error(f"Error downloading image for message {message.id}: {e}")
        
        return None
    
    async def scrape_channel(self, client: TelegramClient, channel_identifier: str, 
                           channel_name: str, days_back: int = 30):
        """Scrape messages from a Telegram channel"""
        self.logger.info(f"Starting scrape for channel: {channel_name}")
        
        try:
            # Get channel entity
            entity = await client.get_entity(channel_identifier)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Collect messages
            messages_data = []
            offset_id = 0
            limit = 100
            
            while True:
                history = await client(GetHistoryRequest(
                    peer=entity,
                    offset_id=offset_id,
                    offset_date=None,
                    add_offset=0,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))
                
                if not history.messages:
                    break
                
                for message in history.messages:
                    # Check if message is within date range
                    if message.date and message.date.replace(tzinfo=None) < start_date:
                        break
                    
                    # Extract message data
                    message_data = self._extract_message_data(message, channel_name)
                    
                    # Download image if present
                    if message_data.has_media:
                        image_path = await self.download_image(client, message, channel_name)
                        message_data.image_path = image_path
                    
                    messages_data.append(asdict(message_data))
                
                # Update offset for next batch
                offset_id = history.messages[-1].id
                
                # Break if no more messages or reached start date
                if len(history.messages) < limit:
                    break
            
            # Save messages to JSON
            if messages_data:
                self._save_messages(messages_data, channel_name)
                self.logger.info(f"Saved {len(messages_data)} messages from {channel_name}")
            else:
                self.logger.warning(f"No messages found for {channel_name}")
            
            return len(messages_data)
            
        except Exception as e:
            self.logger.error(f"Error scraping channel {channel_name}: {e}")
            return 0
    
    def _save_messages(self, messages: List[Dict], channel_name: str):
        """Save messages to JSON file with partitioned structure"""
        # Group messages by date
        messages_by_date = {}
        for msg in messages:
            msg_date = datetime.fromisoformat(msg['message_date'].replace('Z', '+00:00'))
            date_key = msg_date.strftime('%Y-%m-%d')
            
            if date_key not in messages_by_date:
                messages_by_date[date_key] = []
            
            messages_by_date[date_key].append(msg)
        
        # Save each date's messages to separate file
        for date_str, date_messages in messages_by_date.items():
            # Create date directory
            date_dir = self.data_dir / 'telegram_messages' / date_str
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Define file path
            file_path = date_dir / f"{channel_name}.json"
            
            # Save to JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'channel': channel_name,
                    'date': date_str,
                    'message_count': len(date_messages),
                    'messages': date_messages
                }, f, ensure_ascii=False, indent=2, default=str)
    
    async def run(self):
        """Main execution method"""
        self.logger.info("Starting Telegram scraper...")
        
        total_messages = 0
        
        try:
            # Initialize Telegram client
            client = await self.initialize_client()
            
            # Scrape each channel
            for channel_key, channel_identifier in self.channels.items():
                messages_count = await self.scrape_channel(
                    client, channel_identifier, channel_key
                )
                total_messages += messages_count
                
                # Wait between channels to avoid rate limiting
                await asyncio.sleep(5)
            
            # Log completion
            self.logger.info(f"Scraping completed. Total messages: {total_messages}")
            
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}")
            raise
        
        finally:
            # Ensure client is disconnected
            if 'client' in locals():
                await client.disconnect()

def main():
    """Main entry point"""
    scraper = TelegramScraper()
    asyncio.run(scraper.run())

if __name__ == "__main__":
    main()