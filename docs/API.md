# API Documentation

## Overview

The Automotive Sensor Data API provides RESTful endpoints for accessing sensor data, analytics, and system health information.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. In production, implement proper authentication mechanisms.

## Endpoints

### Health Check

#### GET /health

Check the health status of the API and its dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "database_connected": true,
  "kafka_connected": true,
  "spark_connected": true
}
```

### Sensor Data

#### GET /sensor-data

Retrieve sensor data with optional filtering.

**Query Parameters:**
- `vehicle_id` (string, optional): Filter by vehicle ID
- `sensor_type` (string, optional): Filter by sensor type (radar, camera, lidar, etc.)
- `sensor_id` (string, optional): Filter by sensor ID
- `start_time` (datetime, optional): Start time filter (ISO format)
- `end_time` (datetime, optional): End time filter (ISO format)
- `limit` (integer, optional): Number of records to return (1-1000, default: 100)
- `offset` (integer, optional): Number of records to skip (default: 0)

**Example Request:**
```
GET /sensor-data?vehicle_id=VH_12345&sensor_type=radar&limit=50
```

**Response:**
```json
[
  {
    "timestamp": "2024-01-15T10:30:00Z",
    "sensor_id": "radar_001",
    "vehicle_id": "VH_12345",
    "sensor_type": "radar",
    "location": {
      "latitude": 47.4979,
      "longitude": 19.0402
    },
    "measurements": {
      "distance": 150.5,
      "speed": 65.2,
      "angle": 12.3,
      "confidence": 0.95
    },
    "metadata": {
      "firmware_version": "2.1.3",
      "calibration_date": "2024-01-01"
    },
    "quality_score": 0.95
  }
]
```

### Analytics

#### GET /analytics/daily

Get daily analytics summary.

**Query Parameters:**
- `date` (string, optional): Date in YYYY-MM-DD format (default: today)

**Example Request:**
```
GET /analytics/daily?date=2024-01-15
```

**Response:**
```json
{
  "date": "2024-01-15",
  "total_records": 15000,
  "unique_vehicles": 45,
  "unique_sensors": 120,
  "avg_quality_score": 0.92,
  "anomaly_count": 15
}
```

#### GET /analytics/sensor-types

Get analytics grouped by sensor type.

**Query Parameters:**
- `date` (string, optional): Date in YYYY-MM-DD format (default: today)

**Example Request:**
```
GET /analytics/sensor-types?date=2024-01-15
```

**Response:**
```json
[
  {
    "sensor_type": "radar",
    "record_count": 5000,
    "unique_vehicles": 45,
    "avg_quality_score": 0.94,
    "avg_measurements": {
      "distance": 125.3,
      "speed": 58.7
    }
  },
  {
    "sensor_type": "camera",
    "record_count": 4000,
    "unique_vehicles": 42,
    "avg_quality_score": 0.91,
    "avg_measurements": {
      "object_count": 3.2
    }
  }
]
```

#### GET /analytics/vehicles

Get analytics grouped by vehicle.

**Query Parameters:**
- `date` (string, optional): Date in YYYY-MM-DD format (default: today)
- `limit` (integer, optional): Number of vehicles to return (1-100, default: 10)

**Example Request:**
```
GET /analytics/vehicles?date=2024-01-15&limit=5
```

**Response:**
```json
[
  {
    "vehicle_id": "VH_12345",
    "total_readings": 1200,
    "sensor_types_used": 4,
    "avg_quality_score": 0.93,
    "coverage_hours": 8.5
  }
]
```

### Anomalies

#### GET /anomalies

Get anomaly data.

**Query Parameters:**
- `date` (string, optional): Date in YYYY-MM-DD format (default: today)
- `sensor_type` (string, optional): Filter by sensor type
- `limit` (integer, optional): Number of anomalies to return (1-1000, default: 100)

**Example Request:**
```
GET /anomalies?date=2024-01-15&sensor_type=radar&limit=20
```

**Response:**
```json
[
  {
    "timestamp": "2024-01-15T10:30:00Z",
    "sensor_id": "radar_001",
    "vehicle_id": "VH_12345",
    "sensor_type": "radar",
    "location": {
      "latitude": 47.4979,
      "longitude": 19.0402
    },
    "measurements": {
      "distance": 250.0,
      "speed": 65.2,
      "angle": 12.3,
      "confidence": 0.95
    },
    "metadata": {
      "firmware_version": "2.1.3",
      "calibration_date": "2024-01-01"
    },
    "anomaly_score": 1.0
  }
]
```

### Metrics

#### GET /metrics

Get Prometheus metrics for monitoring.

**Response:**
```
# HELP api_requests_total Total API requests
# TYPE api_requests_total counter
api_requests_total{endpoint="/sensor-data",method="GET"} 150
api_requests_total{endpoint="/analytics/daily",method="GET"} 25

# HELP api_request_duration_seconds API request duration
# TYPE api_request_duration_seconds histogram
api_request_duration_seconds_bucket{le="0.1"} 100
api_request_duration_seconds_bucket{le="0.5"} 150
api_request_duration_seconds_bucket{le="1.0"} 175
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid query parameter"
}
```

### 404 Not Found
```json
{
  "detail": "No data found for the specified date"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to fetch sensor data"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. In production, implement appropriate rate limiting based on your requirements.

## Data Models

### SensorData
```json
{
  "timestamp": "string (ISO 8601)",
  "sensor_id": "string",
  "vehicle_id": "string",
  "sensor_type": "string (radar|camera|lidar|ultrasonic|imu|gps)",
  "location": {
    "latitude": "number",
    "longitude": "number"
  },
  "measurements": "object (varies by sensor type)",
  "metadata": "object",
  "quality_score": "number (0.0-1.0, optional)"
}
```

### AnalyticsResponse
```json
{
  "date": "string (YYYY-MM-DD)",
  "total_records": "integer",
  "unique_vehicles": "integer",
  "unique_sensors": "integer",
  "avg_quality_score": "number",
  "anomaly_count": "integer"
}
```

## Examples

### Python Client Example
```python
import requests

# Get sensor data
response = requests.get('http://localhost:8000/sensor-data', params={
    'vehicle_id': 'VH_12345',
    'sensor_type': 'radar',
    'limit': 10
})
data = response.json()

# Get daily analytics
response = requests.get('http://localhost:8000/analytics/daily', params={
    'date': '2024-01-15'
})
analytics = response.json()
```

### cURL Examples
```bash
# Get sensor data
curl "http://localhost:8000/sensor-data?vehicle_id=VH_12345&limit=10"

# Get daily analytics
curl "http://localhost:8000/analytics/daily?date=2024-01-15"

# Get anomalies
curl "http://localhost:8000/anomalies?date=2024-01-15&limit=20"
```

## Interactive Documentation

Visit `/docs` for interactive API documentation powered by Swagger UI, or `/redoc` for ReDoc documentation.
