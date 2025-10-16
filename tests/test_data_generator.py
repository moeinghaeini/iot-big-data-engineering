#!/usr/bin/env python3
"""
Tests for the sensor data generator
"""

import pytest
import json
from datetime import datetime
from src.data_generator.sensor_data_generator import AutomotiveSensorGenerator, SensorData

class TestAutomotiveSensorGenerator:
    """Test cases for AutomotiveSensorGenerator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.generator = AutomotiveSensorGenerator()
    
    def test_sensor_types(self):
        """Test that all expected sensor types are available"""
        expected_types = ['radar', 'camera', 'lidar', 'ultrasonic', 'imu', 'gps']
        assert set(self.generator.sensor_types) == set(expected_types)
    
    def test_generate_sensor_data(self):
        """Test sensor data generation"""
        sensor_data = self.generator.generate_sensor_data()
        
        # Check required fields
        assert hasattr(sensor_data, 'timestamp')
        assert hasattr(sensor_data, 'sensor_id')
        assert hasattr(sensor_data, 'vehicle_id')
        assert hasattr(sensor_data, 'sensor_type')
        assert hasattr(sensor_data, 'location')
        assert hasattr(sensor_data, 'measurements')
        assert hasattr(sensor_data, 'metadata')
        
        # Check data types
        assert isinstance(sensor_data.timestamp, str)
        assert isinstance(sensor_data.sensor_id, str)
        assert isinstance(sensor_data.vehicle_id, str)
        assert isinstance(sensor_data.sensor_type, str)
        assert isinstance(sensor_data.location, dict)
        assert isinstance(sensor_data.measurements, dict)
        assert isinstance(sensor_data.metadata, dict)
        
        # Check sensor type is valid
        assert sensor_data.sensor_type in self.generator.sensor_types
        
        # Check location has required fields
        assert 'latitude' in sensor_data.location
        assert 'longitude' in sensor_data.location
        assert isinstance(sensor_data.location['latitude'], float)
        assert isinstance(sensor_data.location['longitude'], float)
    
    def test_generate_radar_data(self):
        """Test radar data generation"""
        radar_data = self.generator.generate_radar_data("radar_001", "VH_12345")
        
        required_fields = ['distance', 'speed', 'angle', 'confidence', 'target_type', 'relative_velocity']
        for field in required_fields:
            assert field in radar_data
        
        # Check value ranges
        assert 0.5 <= radar_data['distance'] <= 200.0
        assert 0 <= radar_data['speed'] <= 120.0
        assert -180 <= radar_data['angle'] <= 180
        assert 0.7 <= radar_data['confidence'] <= 1.0
        assert radar_data['target_type'] in ['vehicle', 'pedestrian', 'cyclist', 'static_object']
    
    def test_generate_camera_data(self):
        """Test camera data generation"""
        camera_data = self.generator.generate_camera_data("camera_001", "VH_12345")
        
        required_fields = ['object_count', 'lane_detection', 'traffic_signs', 'pedestrian_detection', 'image_quality']
        for field in required_fields:
            assert field in camera_data
        
        # Check value ranges
        assert 0 <= camera_data['object_count'] <= 10
        assert 0 <= camera_data['traffic_signs'] <= 5
        assert 0 <= camera_data['pedestrian_detection'] <= 3
        assert 0.6 <= camera_data['image_quality'] <= 1.0
        
        # Check lane detection structure
        lane_detection = camera_data['lane_detection']
        assert 'left_lane_confidence' in lane_detection
        assert 'right_lane_confidence' in lane_detection
        assert 'lane_width' in lane_detection
    
    def test_generate_batch(self):
        """Test batch generation"""
        batch_size = 10
        batch_data = self.generator.generate_batch(batch_size)
        
        assert len(batch_data) == batch_size
        
        # Check that all items are dictionaries
        for item in batch_data:
            assert isinstance(item, dict)
            assert 'timestamp' in item
            assert 'sensor_id' in item
            assert 'vehicle_id' in item
            assert 'sensor_type' in item
    
    def test_metadata_generation(self):
        """Test metadata generation"""
        for sensor_type in self.generator.sensor_types:
            metadata = self.generator.generate_metadata(sensor_type)
            
            required_fields = ['firmware_version', 'calibration_date', 'manufacturer', 'model', 'temperature', 'humidity']
            for field in required_fields:
                assert field in metadata
            
            # Check specific values
            assert metadata['manufacturer'] == 'Bosch'
            assert metadata['model'].startswith(sensor_type.upper())
            assert -20 <= metadata['temperature'] <= 60
            assert 20 <= metadata['humidity'] <= 80
    
    def test_location_generation(self):
        """Test location generation"""
        location = self.generator.generate_location()
        
        assert 'latitude' in location
        assert 'longitude' in location
        
        # Check that location is within reasonable range of base location
        base_lat = self.generator.base_location['latitude']
        base_lon = self.generator.base_location['longitude']
        
        assert abs(location['latitude'] - base_lat) <= 0.1
        assert abs(location['longitude'] - base_lon) <= 0.1

class TestSensorData:
    """Test cases for SensorData dataclass"""
    
    def test_sensor_data_creation(self):
        """Test SensorData object creation"""
        sensor_data = SensorData(
            timestamp="2024-01-15T10:30:00Z",
            sensor_id="radar_001",
            vehicle_id="VH_12345",
            sensor_type="radar",
            location={"latitude": 47.4979, "longitude": 19.0402},
            measurements={"distance": 150.5, "speed": 65.2},
            metadata={"firmware_version": "2.1.3"}
        )
        
        assert sensor_data.timestamp == "2024-01-15T10:30:00Z"
        assert sensor_data.sensor_id == "radar_001"
        assert sensor_data.vehicle_id == "VH_12345"
        assert sensor_data.sensor_type == "radar"
        assert sensor_data.location["latitude"] == 47.4979
        assert sensor_data.measurements["distance"] == 150.5
        assert sensor_data.metadata["firmware_version"] == "2.1.3"
    
    def test_sensor_data_json_serialization(self):
        """Test JSON serialization of SensorData"""
        from dataclasses import asdict
        
        sensor_data = SensorData(
            timestamp="2024-01-15T10:30:00Z",
            sensor_id="radar_001",
            vehicle_id="VH_12345",
            sensor_type="radar",
            location={"latitude": 47.4979, "longitude": 19.0402},
            measurements={"distance": 150.5, "speed": 65.2},
            metadata={"firmware_version": "2.1.3"}
        )
        
        # Convert to dict and then to JSON
        data_dict = asdict(sensor_data)
        json_str = json.dumps(data_dict)
        
        # Parse back and verify
        parsed_data = json.loads(json_str)
        assert parsed_data["sensor_id"] == "radar_001"
        assert parsed_data["sensor_type"] == "radar"
        assert parsed_data["location"]["latitude"] == 47.4979

if __name__ == "__main__":
    pytest.main([__file__])
