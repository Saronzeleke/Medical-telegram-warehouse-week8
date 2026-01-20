#!/usr/bin/env python3
"""
YOLO Object Detection for Medical Telegram Images
Analyzes downloaded images and categorizes them for enrichment
"""

import os
import csv
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

import cv2
from ultralytics import YOLO
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class YOLODetector:
    def __init__(self, model_path='yolov8n.pt'):
        self.base_dir = Path(__file__).parent.parent
        self.images_dir = self.base_dir / 'data' / 'raw' / 'images'
        self.output_dir = self.base_dir / 'data' / 'processed' / 'yolo_detections'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Load YOLO model
        self.model = self._load_model(model_path)
        
        # COCO class names (YOLOv8 default)
        self.class_names = {
            0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane',
            5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light',
            24: 'bottle', 25: 'wine glass', 26: 'cup', 27: 'fork', 28: 'knife',
            29: 'spoon', 30: 'bowl', 31: 'banana', 32: 'apple', 33: 'sandwich',
            39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife',
            44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple', 48: 'sandwich',
            56: 'chair', 57: 'couch', 58: 'potted plant', 59: 'bed', 60: 'dining table',
            61: 'toilet', 62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote',
            66: 'keyboard', 67: 'cell phone', 68: 'microwave', 69: 'oven',
            70: 'toaster', 71: 'sink', 72: 'refrigerator', 73: 'book', 74: 'clock',
            75: 'vase', 76: 'scissors', 77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'
        }
        
        # Medical product related classes
        self.product_classes = {'bottle', 'box', 'container', 'package', 'pills'}
        
    def _setup_logging(self):
        """Setup logging configuration"""
        log_file = self.base_dir / 'logs' / f'yolo_{datetime.now().strftime("%Y%m%d")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def _load_model(self, model_path: str) -> YOLO:
        """Load YOLO model, download if not present"""
        try:
            model = YOLO(model_path)
            self.logger.info(f"Loaded YOLO model: {model_path}")
            return model
        except Exception as e:
            self.logger.warning(f"Model not found, downloading YOLOv8n: {e}")
            model = YOLO('yolov8n.pt')
            model.save(model_path)
            return model
    
    def find_images(self) -> List[Path]:
        """Find all downloaded images"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(self.images_dir.rglob(f'*{ext}'))
        
        self.logger.info(f"Found {len(image_files)} images for detection")
        return image_files
    
    def extract_message_id(self, image_path: Path) -> Optional[int]:
        """Extract message_id from image filename"""
        try:
            # Filename format: {message_id}.jpg
            message_id = int(image_path.stem.split('.')[0])
            return message_id
        except (ValueError, IndexError):
            # Try to extract from path: images/channel_name/message_id.jpg
            try:
                message_id = int(image_path.stem)
                return message_id
            except ValueError:
                self.logger.warning(f"Could not extract message_id from {image_path}")
                return None
    
    def extract_channel_name(self, image_path: Path) -> Optional[str]:
        """Extract channel name from image path"""
        try:
            # Path format: images/channel_name/message_id.jpg
            channel_name = image_path.parent.name
            return channel_name
        except:
            return None
    
    def categorize_image(self, detections: List[Dict]) -> Tuple[str, float]:
        """
        Categorize image based on detected objects
        
        Categories:
        - promotional: person + product (bottle/container)
        - product_display: product only
        - lifestyle: person only
        - other: neither
        """
        has_person = False
        has_product = False
        max_confidence = 0.0
        
        detected_classes = set()
        confidences = []
        
        for det in detections:
            class_id = det['class_id']
            confidence = det['confidence']
            class_name = self.class_names.get(class_id, 'unknown')
            
            detected_classes.add(class_name)
            confidences.append(confidence)
            max_confidence = max(max_confidence, confidence)
            
            if class_name == 'person':
                has_person = True
            elif class_name in ['bottle', 'cup', 'wine glass'] or 'bottle' in class_name.lower():
                has_product = True
        
        # Apply categorization logic
        if has_person and has_product:
            category = 'promotional'
        elif has_product and not has_person:
            category = 'product_display'
        elif has_person and not has_product:
            category = 'lifestyle'
        else:
            category = 'other'
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return category, avg_confidence, list(detected_classes)
    
    def detect_objects(self, image_path: Path) -> List[Dict]:
        """Run YOLO detection on a single image"""
        try:
            # Run inference
            results = self.model(image_path, conf=0.25, verbose=False)
            
            detections = []
            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    detection = {
                        'class_id': int(box.cls[0]),
                        'class_name': self.class_names.get(int(box.cls[0]), 'unknown'),
                        'confidence': float(box.conf[0]),
                        'bbox': box.xyxy[0].tolist() if box.xyxy is not None else []
                    }
                    detections.append(detection)
            
            self.logger.debug(f"Detected {len(detections)} objects in {image_path.name}")
            return detections
            
        except Exception as e:
            self.logger.error(f"Error detecting objects in {image_path}: {e}")
            return []
    
    def process_image(self, image_path: Path) -> Optional[Dict]:
        """Process a single image and return detection results"""
        message_id = self.extract_message_id(image_path)
        channel_name = self.extract_channel_name(image_path)
        
        if message_id is None:
            return None
        
        # Run object detection
        detections = self.detect_objects(image_path)
        
        # Categorize image
        category, avg_confidence, detected_classes = self.categorize_image(detections)
        
        # Prepare result
        result = {
            'message_id': message_id,
            'channel_name': channel_name,
            'image_path': str(image_path.relative_to(self.base_dir)),
            'detection_count': len(detections),
            'detected_classes': ', '.join(detected_classes) if detected_classes else 'none',
            'image_category': category,
            'confidence_score': avg_confidence,
            'has_person': any(d['class_name'] == 'person' for d in detections),
            'has_product': any('bottle' in d['class_name'].lower() for d in detections),
            'processed_at': datetime.now().isoformat(),
            'detections': detections  # Raw detection data
        }
        
        return result
    
    def save_to_csv(self, results: List[Dict]):
        """Save detection results to CSV"""
        if not results:
            self.logger.warning("No results to save")
            return
        
        csv_path = self.output_dir / f'yolo_detections_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        # Flatten results for CSV
        flat_results = []
        for result in results:
            flat_result = {k: v for k, v in result.items() if k != 'detections'}
            flat_results.append(flat_result)
        
        df = pd.DataFrame(flat_results)
        df.to_csv(csv_path, index=False)
        self.logger.info(f"Saved {len(df)} detection results to {csv_path}")
        
        # Also save to latest.csv for easy reference
        latest_path = self.output_dir / 'latest_detections.csv'
        df.to_csv(latest_path, index=False)
        
        return csv_path
    
    def load_to_postgres(self, results: List[Dict]):
        """Load detection results to PostgreSQL"""
        if not results:
            return
        
        try:
            # Create database engine
            db_user = os.getenv('POSTGRES_USER', 'medical_user')
            db_password = os.getenv('POSTGRES_PASSWORD', 'secure_password')
            db_host = os.getenv('POSTGRES_HOST', 'localhost')
            db_port = os.getenv('POSTGRES_PORT', '5432')
            db_name = os.getenv('POSTGRES_DB', 'medical_warehouse')
            
            engine = create_engine(
                f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
            )
            
            # Create table if not exists
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS raw.yolo_detections (
                id SERIAL PRIMARY KEY,
                message_id BIGINT,
                channel_name VARCHAR(255),
                image_path VARCHAR(500),
                detection_count INTEGER,
                detected_classes TEXT,
                image_category VARCHAR(50),
                confidence_score DECIMAL(5,4),
                has_person BOOLEAN,
                has_product BOOLEAN,
                processed_at TIMESTAMP,
                loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_yolo_message_id ON raw.yolo_detections(message_id);
            CREATE INDEX IF NOT EXISTS idx_yolo_category ON raw.yolo_detections(image_category);
            """
            
            with engine.connect() as conn:
                conn.execute(create_table_sql)
                conn.commit()
            
            # Load results
            flat_results = []
            for result in results:
                flat_result = {k: v for k, v in result.items() if k != 'detections'}
                flat_results.append(flat_result)
            
            df = pd.DataFrame(flat_results)
            df.to_sql(
                name='yolo_detections',
                schema='raw',
                con=engine,
                if_exists='append',
                index=False
            )
            
            self.logger.info(f"Loaded {len(df)} detection results to PostgreSQL")
            
        except Exception as e:
            self.logger.error(f"Error loading to PostgreSQL: {e}")
    
    def run(self, max_images: int = None):
        """Main execution method"""
        self.logger.info("Starting YOLO object detection pipeline...")
        
        # Find images
        image_files = self.find_images()
        
        if max_images:
            image_files = image_files[:max_images]
            self.logger.info(f"Limiting to {max_images} images for processing")
        
        # Process images
        results = []
        processed_count = 0
        error_count = 0
        
        for i, image_path in enumerate(image_files, 1):
            try:
                self.logger.info(f"Processing image {i}/{len(image_files)}: {image_path.name}")
                
                result = self.process_image(image_path)
                if result:
                    results.append(result)
                    processed_count += 1
                
                # Progress update
                if i % 10 == 0:
                    self.logger.info(f"Progress: {i}/{len(image_files)} images processed")
                    
            except Exception as e:
                self.logger.error(f"Error processing {image_path}: {e}")
                error_count += 1
        
        # Save and load results
        if results:
            csv_path = self.save_to_csv(results)
            self.load_to_postgres(results)
            
            # Summary statistics
            categories = [r['image_category'] for r in results]
            category_counts = {cat: categories.count(cat) for cat in set(categories)}
            
            self.logger.info("=" * 50)
            self.logger.info("YOLO DETECTION SUMMARY")
            self.logger.info("=" * 50)
            self.logger.info(f"Total images processed: {processed_count}")
            self.logger.info(f"Errors encountered: {error_count}")
            self.logger.info("Category distribution:")
            for cat, count in category_counts.items():
                percentage = (count / processed_count) * 100
                self.logger.info(f"  {cat}: {count} ({percentage:.1f}%)")
            self.logger.info(f"Results saved to: {csv_path}")
            self.logger.info("=" * 50)
        else:
            self.logger.warning("No images were successfully processed")
        
        return results

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YOLO Object Detection for Medical Images')
    parser.add_argument('--max-images', type=int, help='Maximum number of images to process')
    parser.add_argument('--model', default='yolov8n.pt', help='Path to YOLO model')
    
    args = parser.parse_args()
    
    detector = YOLODetector(model_path=args.model)
    results = detector.run(max_images=args.max_images)
    
    print(f"\nProcessing complete. Results: {len(results) if results else 0} images analyzed.")

if __name__ == '__main__':
    main()