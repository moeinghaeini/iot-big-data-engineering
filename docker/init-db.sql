-- Initialize sensor data database
CREATE DATABASE IF NOT EXISTS sensor_data;

-- Create tables for sensor data
CREATE TABLE IF NOT EXISTS sensor_quality_checked (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    sensor_id VARCHAR(50) NOT NULL,
    vehicle_id VARCHAR(50) NOT NULL,
    sensor_type VARCHAR(20) NOT NULL,
    location JSONB NOT NULL,
    measurements JSONB NOT NULL,
    metadata JSONB NOT NULL,
    quality_score DECIMAL(3,2),
    anomaly_score DECIMAL(3,2) DEFAULT 0.0,
    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sensor_analytics (
    id SERIAL PRIMARY KEY,
    processing_date DATE NOT NULL,
    sensor_type VARCHAR(20) NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    record_count INTEGER NOT NULL,
    unique_vehicles INTEGER NOT NULL,
    unique_sensors INTEGER NOT NULL,
    avg_quality_score DECIMAL(3,2),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sensor_anomalies (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    sensor_id VARCHAR(50) NOT NULL,
    vehicle_id VARCHAR(50) NOT NULL,
    sensor_type VARCHAR(20) NOT NULL,
    location JSONB NOT NULL,
    measurements JSONB NOT NULL,
    metadata JSONB NOT NULL,
    anomaly_score DECIMAL(3,2) NOT NULL,
    processing_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sensor_quality_timestamp ON sensor_quality_checked(timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_quality_vehicle_id ON sensor_quality_checked(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_sensor_quality_sensor_type ON sensor_quality_checked(sensor_type);
CREATE INDEX IF NOT EXISTS idx_sensor_quality_sensor_id ON sensor_quality_checked(sensor_id);
CREATE INDEX IF NOT EXISTS idx_sensor_quality_quality_score ON sensor_quality_checked(quality_score);

CREATE INDEX IF NOT EXISTS idx_sensor_analytics_date ON sensor_analytics(processing_date);
CREATE INDEX IF NOT EXISTS idx_sensor_analytics_sensor_type ON sensor_analytics(sensor_type);

CREATE INDEX IF NOT EXISTS idx_sensor_anomalies_timestamp ON sensor_anomalies(timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_anomalies_vehicle_id ON sensor_anomalies(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_sensor_anomalies_sensor_type ON sensor_anomalies(sensor_type);
CREATE INDEX IF NOT EXISTS idx_sensor_anomalies_anomaly_score ON sensor_anomalies(anomaly_score);

-- Create views for common queries
CREATE OR REPLACE VIEW daily_sensor_summary AS
SELECT 
    DATE(timestamp) as date,
    sensor_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT vehicle_id) as unique_vehicles,
    COUNT(DISTINCT sensor_id) as unique_sensors,
    AVG(quality_score) as avg_quality_score,
    COUNT(CASE WHEN anomaly_score > 0 THEN 1 END) as anomaly_count
FROM sensor_quality_checked
GROUP BY DATE(timestamp), sensor_type;

CREATE OR REPLACE VIEW vehicle_daily_summary AS
SELECT 
    DATE(timestamp) as date,
    vehicle_id,
    COUNT(*) as total_readings,
    COUNT(DISTINCT sensor_type) as sensor_types_used,
    COUNT(DISTINCT sensor_id) as unique_sensors,
    AVG(quality_score) as avg_quality_score,
    MIN(timestamp) as first_reading,
    MAX(timestamp) as last_reading
FROM sensor_quality_checked
GROUP BY DATE(timestamp), vehicle_id;
