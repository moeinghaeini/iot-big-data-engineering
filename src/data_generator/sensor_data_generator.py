#!/usr/bin/env python3
"""
Automotive Sensor Data Generator
Simulates real-time sensor data from automotive systems (radar, camera, control electronics)
"""

import json
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any
import argparse
import logging
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SensorData:
    """Data class for sensor measurements"""
    timestamp: str
    sensor_id: str
    vehicle_id: str
    sensor_type: str
    location: Dict[str, float]
    measurements: Dict[str, Any]
    metadata: Dict[str, Any]

class AutomotiveSensorGenerator:
    """Generates realistic automotive sensor data"""
    
    def __init__(self):
        self.sensor_types = ['radar', 'camera', 'lidar', 'ultrasonic', 'imu', 'gps']
        self.vehicle_ids = [f"VH_{i:05d}" for i in range(1, 1001)]
        self.sensor_ids = [f"{sensor_type}_{i:03d}" for sensor_type in self.sensor_types for i in range(1, 101)]
        
        # Budapest area coordinates (near Bosch Hatvan plant)
        self.base_location = {
            "latitude": 47.4979,
            "longitude": 19.0402
        }
    
    def generate_radar_data(self, sensor_id: str, vehicle_id: str) -> Dict[str, Any]:
        """Generate radar sensor measurements"""
        return {
            "distance": round(random.uniform(0.5, 200.0), 2),
            "speed": round(random.uniform(0, 120.0), 2),
            "angle": round(random.uniform(-180, 180), 2),
            "confidence": round(random.uniform(0.7, 1.0), 3),
            "target_type": random.choice(['vehicle', 'pedestrian', 'cyclist', 'static_object']),
            "relative_velocity": round(random.uniform(-50, 50), 2)
        }
    
    def generate_camera_data(self, sensor_id: str, vehicle_id: str) -> Dict[str, Any]:
        """Generate camera sensor measurements"""
        return {
            "object_count": random.randint(0, 10),
            "lane_detection": {
                "left_lane_confidence": round(random.uniform(0.5, 1.0), 3),
                "right_lane_confidence": round(random.uniform(0.5, 1.0), 3),
                "lane_width": round(random.uniform(3.0, 4.5), 2)
            },
            "traffic_signs": random.randint(0, 5),
            "pedestrian_detection": random.randint(0, 3),
            "image_quality": round(random.uniform(0.6, 1.0), 3)
        }
    
    def generate_lidar_data(self, sensor_id: str, vehicle_id: str) -> Dict[str, Any]:
        """Generate LiDAR sensor measurements"""
        return {
            "point_cloud_size": random.randint(1000, 100000),
            "detected_objects": random.randint(0, 20),
            "range_accuracy": round(random.uniform(0.01, 0.05), 4),
            "angular_resolution": round(random.uniform(0.1, 0.5), 2),
            "scan_frequency": random.choice([10, 20, 30])
        }
    
    def generate_ultrasonic_data(self, sensor_id: str, vehicle_id: str) -> Dict[str, Any]:
        """Generate ultrasonic sensor measurements"""
        return {
            "distance": round(random.uniform(0.1, 5.0), 3),
            "detection_angle": round(random.uniform(30, 120), 1),
            "signal_strength": round(random.uniform(0.5, 1.0), 3),
            "temperature_compensation": round(random.uniform(-2.0, 2.0), 2)
        }
    
    def generate_imu_data(self, sensor_id: str, vehicle_id: str) -> Dict[str, Any]:
        """Generate IMU sensor measurements"""
        return {
            "acceleration": {
                "x": round(random.uniform(-2.0, 2.0), 3),
                "y": round(random.uniform(-2.0, 2.0), 3),
                "z": round(random.uniform(9.0, 11.0), 3)
            },
            "gyroscope": {
                "x": round(random.uniform(-0.5, 0.5), 4),
                "y": round(random.uniform(-0.5, 0.5), 4),
                "z": round(random.uniform(-0.5, 0.5), 4)
            },
            "magnetometer": {
                "x": round(random.uniform(-50, 50), 2),
                "y": round(random.uniform(-50, 50), 2),
                "z": round(random.uniform(-50, 50), 2)
            }
        }
    
    def generate_gps_data(self, sensor_id: str, vehicle_id: str) -> Dict[str, Any]:
        """Generate GPS sensor measurements"""
        return {
            "latitude": round(self.base_location["latitude"] + random.uniform(-0.01, 0.01), 6),
            "longitude": round(self.base_location["longitude"] + random.uniform(-0.01, 0.01), 6),
            "altitude": round(random.uniform(100, 200), 2),
            "speed": round(random.uniform(0, 120), 2),
            "heading": round(random.uniform(0, 360), 2),
            "accuracy": round(random.uniform(1, 10), 2),
            "satellites": random.randint(4, 12)
        }
    
    def generate_location(self) -> Dict[str, float]:
        """Generate vehicle location with some variation"""
        return {
            "latitude": round(self.base_location["latitude"] + random.uniform(-0.1, 0.1), 6),
            "longitude": round(self.base_location["longitude"] + random.uniform(-0.1, 0.1), 6)
        }
    
    def generate_metadata(self, sensor_type: str) -> Dict[str, Any]:
        """Generate sensor metadata"""
        return {
            "firmware_version": f"{random.randint(1, 3)}.{random.randint(0, 5)}.{random.randint(0, 9)}",
            "calibration_date": "2024-01-01",
            "manufacturer": "Bosch",
            "model": f"{sensor_type.upper()}_SENSOR_V{random.randint(1, 3)}",
            "temperature": round(random.uniform(-20, 60), 1),
            "humidity": round(random.uniform(20, 80), 1)
        }
    
    def generate_sensor_data(self) -> SensorData:
        """Generate a complete sensor data record"""
        sensor_type = random.choice(self.sensor_types)
        sensor_id = random.choice([sid for sid in self.sensor_ids if sensor_type in sid])
        vehicle_id = random.choice(self.vehicle_ids)
        
        # Generate measurements based on sensor type
        measurement_generators = {
            'radar': self.generate_radar_data,
            'camera': self.generate_camera_data,
            'lidar': self.generate_lidar_data,
            'ultrasonic': self.generate_ultrasonic_data,
            'imu': self.generate_imu_data,
            'gps': self.generate_gps_data
        }
        
        measurements = measurement_generators[sensor_type](sensor_id, vehicle_id)
        
        return SensorData(
            timestamp=datetime.now(timezone.utc).isoformat(),
            sensor_id=sensor_id,
            vehicle_id=vehicle_id,
            sensor_type=sensor_type,
            location=self.generate_location(),
            measurements=measurements,
            metadata=self.generate_metadata(sensor_type)
        )
    
    def generate_batch(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate a batch of sensor data records"""
        return [asdict(self.generate_sensor_data()) for _ in range(count)]

def main():
    """Main function to run the data generator"""
    parser = argparse.ArgumentParser(description='Generate automotive sensor data')
    parser.add_argument('--count', type=int, default=1000, help='Number of records to generate')
    parser.add_argument('--output', type=str, default='sensor_data.json', help='Output file path')
    parser.add_argument('--stream', action='store_true', help='Stream data continuously')
    parser.add_argument('--interval', type=float, default=1.0, help='Streaming interval in seconds')
    
    args = parser.parse_args()
    
    generator = AutomotiveSensorGenerator()
    
    if args.stream:
        logger.info(f"Starting continuous data streaming (interval: {args.interval}s)")
        try:
            while True:
                data = generator.generate_sensor_data()
                print(json.dumps(asdict(data)))
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Data streaming stopped")
    else:
        logger.info(f"Generating {args.count} sensor data records...")
        batch_data = generator.generate_batch(args.count)
        
        with open(args.output, 'w') as f:
            json.dump(batch_data, f, indent=2)
        
        logger.info(f"Generated {args.count} records and saved to {args.output}")

if __name__ == "__main__":
    main()
