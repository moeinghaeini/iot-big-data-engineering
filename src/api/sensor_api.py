#!/usr/bin/env python3
"""
REST API for Automotive Sensor Data
Provides endpoints for querying sensor data, analytics, and system health
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uvicorn
import logging
import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'API request duration')

# FastAPI app
app = FastAPI(
    title="Automotive Sensor Data API",
    description="REST API for automotive sensor data analytics and monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/sensor_data")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Pydantic models
class SensorData(BaseModel):
    timestamp: datetime
    sensor_id: str
    vehicle_id: str
    sensor_type: str
    location: Dict[str, float]
    measurements: Dict[str, Any]
    metadata: Dict[str, Any]
    quality_score: Optional[float] = None

class AnalyticsResponse(BaseModel):
    date: str
    total_records: int
    unique_vehicles: int
    unique_sensors: int
    avg_quality_score: float
    anomaly_count: int

class SensorTypeAnalytics(BaseModel):
    sensor_type: str
    record_count: int
    unique_vehicles: int
    avg_quality_score: float
    avg_measurements: Dict[str, Any]

class VehicleAnalytics(BaseModel):
    vehicle_id: str
    total_readings: int
    sensor_types_used: int
    avg_quality_score: float
    coverage_hours: float

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database_connected: bool
    kafka_connected: bool
    spark_connected: bool

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Middleware for metrics
@app.middleware("http")
async def add_metrics(request, call_next):
    start_time = datetime.now()
    
    response = await call_next(request)
    
    duration = (datetime.now() - start_time).total_seconds()
    REQUEST_DURATION.observe(duration)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    
    return response

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Automotive Sensor Data API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_connected = False
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_connected = True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
        
        # Check Kafka connection (simplified)
        kafka_connected = True  # In real implementation, check Kafka cluster
        
        # Check Spark connection (simplified)
        spark_connected = True  # In real implementation, check Spark cluster
        
        status = "healthy" if all([db_connected, kafka_connected, spark_connected]) else "degraded"
        
        return HealthResponse(
            status=status,
            timestamp=datetime.now(),
            database_connected=db_connected,
            kafka_connected=kafka_connected,
            spark_connected=spark_connected
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.get("/sensor-data", response_model=List[SensorData])
async def get_sensor_data(
    vehicle_id: Optional[str] = Query(None, description="Filter by vehicle ID"),
    sensor_type: Optional[str] = Query(None, description="Filter by sensor type"),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    db = Depends(get_db)
):
    """Get sensor data with optional filters"""
    try:
        query = """
        SELECT timestamp, sensor_id, vehicle_id, sensor_type, 
               location, measurements, metadata, quality_score
        FROM sensor_quality_checked
        WHERE 1=1
        """
        params = {}
        
        if vehicle_id:
            query += " AND vehicle_id = :vehicle_id"
            params["vehicle_id"] = vehicle_id
        
        if sensor_type:
            query += " AND sensor_type = :sensor_type"
            params["sensor_type"] = sensor_type
        
        if sensor_id:
            query += " AND sensor_id = :sensor_id"
            params["sensor_id"] = sensor_id
        
        if start_time:
            query += " AND timestamp >= :start_time"
            params["start_time"] = start_time
        
        if end_time:
            query += " AND timestamp <= :end_time"
            params["end_time"] = end_time
        
        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
        
        result = db.execute(text(query), params)
        rows = result.fetchall()
        
        sensor_data = []
        for row in rows:
            sensor_data.append(SensorData(
                timestamp=row.timestamp,
                sensor_id=row.sensor_id,
                vehicle_id=row.vehicle_id,
                sensor_type=row.sensor_type,
                location=json.loads(row.location) if isinstance(row.location, str) else row.location,
                measurements=json.loads(row.measurements) if isinstance(row.measurements, str) else row.measurements,
                metadata=json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata,
                quality_score=row.quality_score
            ))
        
        return sensor_data
        
    except Exception as e:
        logger.error(f"Error fetching sensor data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch sensor data")

@app.get("/analytics/daily", response_model=AnalyticsResponse)
async def get_daily_analytics(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db = Depends(get_db)
):
    """Get daily analytics summary"""
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        
        query = """
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT vehicle_id) as unique_vehicles,
            COUNT(DISTINCT sensor_id) as unique_sensors,
            AVG(quality_score) as avg_quality_score,
            COUNT(CASE WHEN anomaly_score > 0 THEN 1 END) as anomaly_count
        FROM sensor_quality_checked
        WHERE DATE(timestamp) = :date
        """
        
        result = db.execute(text(query), {"date": target_date})
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="No data found for the specified date")
        
        return AnalyticsResponse(
            date=target_date,
            total_records=row.total_records,
            unique_vehicles=row.unique_vehicles,
            unique_sensors=row.unique_sensors,
            avg_quality_score=float(row.avg_quality_score) if row.avg_quality_score else 0.0,
            anomaly_count=row.anomaly_count
        )
        
    except Exception as e:
        logger.error(f"Error fetching daily analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch daily analytics")

@app.get("/analytics/sensor-types", response_model=List[SensorTypeAnalytics])
async def get_sensor_type_analytics(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db = Depends(get_db)
):
    """Get analytics by sensor type"""
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        
        query = """
        SELECT 
            sensor_type,
            COUNT(*) as record_count,
            COUNT(DISTINCT vehicle_id) as unique_vehicles,
            AVG(quality_score) as avg_quality_score,
            AVG(CASE WHEN sensor_type = 'radar' THEN (measurements->>'distance')::float END) as avg_distance,
            AVG(CASE WHEN sensor_type = 'camera' THEN (measurements->>'object_count')::int END) as avg_object_count,
            AVG(CASE WHEN sensor_type = 'gps' THEN (measurements->>'speed')::float END) as avg_speed
        FROM sensor_quality_checked
        WHERE DATE(timestamp) = :date
        GROUP BY sensor_type
        ORDER BY record_count DESC
        """
        
        result = db.execute(text(query), {"date": target_date})
        rows = result.fetchall()
        
        analytics = []
        for row in rows:
            avg_measurements = {}
            if row.avg_distance:
                avg_measurements["distance"] = float(row.avg_distance)
            if row.avg_object_count:
                avg_measurements["object_count"] = int(row.avg_object_count)
            if row.avg_speed:
                avg_measurements["speed"] = float(row.avg_speed)
            
            analytics.append(SensorTypeAnalytics(
                sensor_type=row.sensor_type,
                record_count=row.record_count,
                unique_vehicles=row.unique_vehicles,
                avg_quality_score=float(row.avg_quality_score) if row.avg_quality_score else 0.0,
                avg_measurements=avg_measurements
            ))
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error fetching sensor type analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch sensor type analytics")

@app.get("/analytics/vehicles", response_model=List[VehicleAnalytics])
async def get_vehicle_analytics(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    limit: int = Query(10, ge=1, le=100, description="Number of vehicles to return"),
    db = Depends(get_db)
):
    """Get analytics by vehicle"""
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        
        query = """
        SELECT 
            vehicle_id,
            COUNT(*) as total_readings,
            COUNT(DISTINCT sensor_type) as sensor_types_used,
            AVG(quality_score) as avg_quality_score,
            (MAX(EXTRACT(EPOCH FROM timestamp)) - MIN(EXTRACT(EPOCH FROM timestamp))) / 3600 as coverage_hours
        FROM sensor_quality_checked
        WHERE DATE(timestamp) = :date
        GROUP BY vehicle_id
        ORDER BY total_readings DESC
        LIMIT :limit
        """
        
        result = db.execute(text(query), {"date": target_date, "limit": limit})
        rows = result.fetchall()
        
        analytics = []
        for row in rows:
            analytics.append(VehicleAnalytics(
                vehicle_id=row.vehicle_id,
                total_readings=row.total_readings,
                sensor_types_used=row.sensor_types_used,
                avg_quality_score=float(row.avg_quality_score) if row.avg_quality_score else 0.0,
                coverage_hours=float(row.coverage_hours) if row.coverage_hours else 0.0
            ))
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error fetching vehicle analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch vehicle analytics")

@app.get("/anomalies")
async def get_anomalies(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    sensor_type: Optional[str] = Query(None, description="Filter by sensor type"),
    limit: int = Query(100, ge=1, le=1000, description="Number of anomalies to return"),
    db = Depends(get_db)
):
    """Get anomaly data"""
    try:
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        
        query = """
        SELECT timestamp, sensor_id, vehicle_id, sensor_type, 
               location, measurements, metadata, anomaly_score
        FROM sensor_anomalies
        WHERE DATE(timestamp) = :date
        """
        params = {"date": target_date}
        
        if sensor_type:
            query += " AND sensor_type = :sensor_type"
            params["sensor_type"] = sensor_type
        
        query += " ORDER BY anomaly_score DESC, timestamp DESC LIMIT :limit"
        params["limit"] = limit
        
        result = db.execute(text(query), params)
        rows = result.fetchall()
        
        anomalies = []
        for row in rows:
            anomalies.append({
                "timestamp": row.timestamp.isoformat(),
                "sensor_id": row.sensor_id,
                "vehicle_id": row.vehicle_id,
                "sensor_type": row.sensor_type,
                "location": json.loads(row.location) if isinstance(row.location, str) else row.location,
                "measurements": json.loads(row.measurements) if isinstance(row.measurements, str) else row.measurements,
                "metadata": json.loads(row.metadata) if isinstance(row.metadata, str) else row.metadata,
                "anomaly_score": float(row.anomaly_score)
            })
        
        return anomalies
        
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch anomalies")

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    uvicorn.run(
        "sensor_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
