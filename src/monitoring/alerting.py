#!/usr/bin/env python3
"""
Alerting System for Automotive Sensor Data Pipeline
Monitors system health and data quality, sends alerts when thresholds are exceeded
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import requests
from sqlalchemy import create_engine, text
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertType(Enum):
    DATA_QUALITY = "data_quality"
    SYSTEM_HEALTH = "system_health"
    PERFORMANCE = "performance"
    ANOMALY = "anomaly"

@dataclass
class Alert:
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    timestamp: datetime
    metadata: Dict[str, Any]
    resolved: bool = False

class AlertingSystem:
    """Main alerting system for monitoring sensor data pipeline"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/sensor_data")
        self.engine = create_engine(self.database_url)
        
        # Alert thresholds
        self.thresholds = {
            "data_quality_min": 0.8,
            "anomaly_rate_max": 0.05,
            "processing_latency_max": 30,  # seconds
            "error_rate_max": 0.01,
            "throughput_min": 1000,  # records per minute
            "system_cpu_max": 80,  # percentage
            "system_memory_max": 85,  # percentage
            "disk_usage_max": 90  # percentage
        }
        
        # Notification channels
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.email_config = {
            "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "username": os.getenv("EMAIL_USERNAME"),
            "password": os.getenv("EMAIL_PASSWORD"),
            "from_email": os.getenv("FROM_EMAIL"),
            "to_emails": os.getenv("TO_EMAILS", "").split(",")
        }
    
    async def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        logger.info("Starting monitoring cycle")
        
        try:
            # Check data quality
            await self.check_data_quality()
            
            # Check system health
            await self.check_system_health()
            
            # Check performance metrics
            await self.check_performance_metrics()
            
            # Check for anomalies
            await self.check_anomalies()
            
            logger.info("Monitoring cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            await self.send_alert(Alert(
                id=f"monitoring_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                type=AlertType.SYSTEM_HEALTH,
                severity=AlertSeverity.CRITICAL,
                title="Monitoring System Error",
                description=f"Monitoring cycle failed: {str(e)}",
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            ))
    
    async def check_data_quality(self):
        """Check data quality metrics"""
        try:
            with self.engine.connect() as conn:
                # Check average quality score for last hour
                query = """
                SELECT 
                    AVG(quality_score) as avg_quality,
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN quality_score < 0.6 THEN 1 END) as low_quality_count
                FROM sensor_quality_checked
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
                """
                
                result = conn.execute(text(query))
                row = result.fetchone()
                
                if row:
                    avg_quality = float(row.avg_quality) if row.avg_quality else 0.0
                    total_records = row.total_records
                    low_quality_count = row.low_quality_count
                    
                    # Check if quality is below threshold
                    if avg_quality < self.thresholds["data_quality_min"]:
                        await self.send_alert(Alert(
                            id=f"data_quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            type=AlertType.DATA_QUALITY,
                            severity=AlertSeverity.WARNING,
                            title="Data Quality Below Threshold",
                            description=f"Average data quality score is {avg_quality:.3f}, below threshold of {self.thresholds['data_quality_min']}",
                            timestamp=datetime.now(),
                            metadata={
                                "avg_quality": avg_quality,
                                "total_records": total_records,
                                "low_quality_count": low_quality_count,
                                "threshold": self.thresholds["data_quality_min"]
                            }
                        ))
                    
                    # Check if too many low quality records
                    low_quality_rate = low_quality_count / total_records if total_records > 0 else 0
                    if low_quality_rate > 0.1:  # More than 10% low quality
                        await self.send_alert(Alert(
                            id=f"low_quality_rate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            type=AlertType.DATA_QUALITY,
                            severity=AlertSeverity.CRITICAL,
                            title="High Low Quality Data Rate",
                            description=f"Low quality data rate is {low_quality_rate:.1%}, above acceptable threshold",
                            timestamp=datetime.now(),
                            metadata={
                                "low_quality_rate": low_quality_rate,
                                "low_quality_count": low_quality_count,
                                "total_records": total_records
                            }
                        ))
                
        except Exception as e:
            logger.error(f"Error checking data quality: {e}")
    
    async def check_system_health(self):
        """Check system health metrics"""
        try:
            # Check database connectivity
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Check if we're receiving data
            with self.engine.connect() as conn:
                query = """
                SELECT COUNT(*) as recent_records
                FROM sensor_quality_checked
                WHERE timestamp >= NOW() - INTERVAL '5 minutes'
                """
                result = conn.execute(text(query))
                row = result.fetchone()
                
                if row and row.recent_records == 0:
                    await self.send_alert(Alert(
                        id=f"no_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        type=AlertType.SYSTEM_HEALTH,
                        severity=AlertSeverity.CRITICAL,
                        title="No Data Received",
                        description="No sensor data received in the last 5 minutes",
                        timestamp=datetime.now(),
                        metadata={"time_window": "5 minutes"}
                    ))
        
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            await self.send_alert(Alert(
                id=f"system_health_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                type=AlertType.SYSTEM_HEALTH,
                severity=AlertSeverity.CRITICAL,
                title="System Health Check Failed",
                description=f"System health check failed: {str(e)}",
                timestamp=datetime.now(),
                metadata={"error": str(e)}
            ))
    
    async def check_performance_metrics(self):
        """Check performance metrics"""
        try:
            with self.engine.connect() as conn:
                # Check processing latency
                query = """
                SELECT 
                    AVG(EXTRACT(EPOCH FROM (processing_timestamp - timestamp))) as avg_latency,
                    MAX(EXTRACT(EPOCH FROM (processing_timestamp - timestamp))) as max_latency
                FROM sensor_quality_checked
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
                AND processing_timestamp IS NOT NULL
                """
                
                result = conn.execute(text(query))
                row = result.fetchone()
                
                if row and row.avg_latency:
                    avg_latency = float(row.avg_latency)
                    max_latency = float(row.max_latency) if row.max_latency else 0.0
                    
                    if avg_latency > self.thresholds["processing_latency_max"]:
                        await self.send_alert(Alert(
                            id=f"high_latency_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            type=AlertType.PERFORMANCE,
                            severity=AlertSeverity.WARNING,
                            title="High Processing Latency",
                            description=f"Average processing latency is {avg_latency:.2f}s, above threshold of {self.thresholds['processing_latency_max']}s",
                            timestamp=datetime.now(),
                            metadata={
                                "avg_latency": avg_latency,
                                "max_latency": max_latency,
                                "threshold": self.thresholds["processing_latency_max"]
                            }
                        ))
                
                # Check throughput
                query = """
                SELECT COUNT(*) as record_count
                FROM sensor_quality_checked
                WHERE timestamp >= NOW() - INTERVAL '1 minute'
                """
                
                result = conn.execute(text(query))
                row = result.fetchone()
                
                if row:
                    throughput = row.record_count
                    if throughput < self.thresholds["throughput_min"]:
                        await self.send_alert(Alert(
                            id=f"low_throughput_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            type=AlertType.PERFORMANCE,
                            severity=AlertSeverity.WARNING,
                            title="Low Throughput",
                            description=f"Throughput is {throughput} records/minute, below threshold of {self.thresholds['throughput_min']}",
                            timestamp=datetime.now(),
                            metadata={
                                "throughput": throughput,
                                "threshold": self.thresholds["throughput_min"]
                            }
                        ))
        
        except Exception as e:
            logger.error(f"Error checking performance metrics: {e}")
    
    async def check_anomalies(self):
        """Check for anomalies in sensor data"""
        try:
            with self.engine.connect() as conn:
                # Check anomaly rate
                query = """
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN anomaly_score > 0 THEN 1 END) as anomaly_count
                FROM sensor_quality_checked
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
                """
                
                result = conn.execute(text(query))
                row = result.fetchone()
                
                if row and row.total_records > 0:
                    anomaly_rate = row.anomaly_count / row.total_records
                    
                    if anomaly_rate > self.thresholds["anomaly_rate_max"]:
                        await self.send_alert(Alert(
                            id=f"high_anomaly_rate_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            type=AlertType.ANOMALY,
                            severity=AlertSeverity.WARNING,
                            title="High Anomaly Rate",
                            description=f"Anomaly rate is {anomaly_rate:.1%}, above threshold of {self.thresholds['anomaly_rate_max']:.1%}",
                            timestamp=datetime.now(),
                            metadata={
                                "anomaly_rate": anomaly_rate,
                                "anomaly_count": row.anomaly_count,
                                "total_records": row.total_records,
                                "threshold": self.thresholds["anomaly_rate_max"]
                            }
                        ))
        
        except Exception as e:
            logger.error(f"Error checking anomalies: {e}")
    
    async def send_alert(self, alert: Alert):
        """Send alert through configured channels"""
        logger.info(f"Sending alert: {alert.title} - {alert.severity.value}")
        
        # Send to Slack
        if self.slack_webhook:
            await self.send_slack_alert(alert)
        
        # Send email for critical alerts
        if alert.severity == AlertSeverity.CRITICAL and self.email_config["username"]:
            await self.send_email_alert(alert)
        
        # Store alert in database
        await self.store_alert(alert)
    
    async def send_slack_alert(self, alert: Alert):
        """Send alert to Slack"""
        try:
            color = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.WARNING: "#ff9500",
                AlertSeverity.CRITICAL: "#ff0000"
            }[alert.severity]
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": alert.title,
                        "text": alert.description,
                        "fields": [
                            {
                                "title": "Type",
                                "value": alert.type.value,
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": alert.timestamp.isoformat(),
                                "short": True
                            }
                        ],
                        "footer": "Sensor Data Pipeline",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    async def send_email_alert(self, alert: Alert):
        """Send alert via email"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_config["from_email"]
            msg['To'] = ", ".join(self.email_config["to_emails"])
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            body = f"""
            Alert Details:
            
            Title: {alert.title}
            Description: {alert.description}
            Type: {alert.type.value}
            Severity: {alert.severity.value.upper()}
            Timestamp: {alert.timestamp.isoformat()}
            
            Metadata:
            {json.dumps(alert.metadata, indent=2)}
            
            This is an automated alert from the Sensor Data Pipeline monitoring system.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"])
            server.starttls()
            server.login(self.email_config["username"], self.email_config["password"])
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    async def store_alert(self, alert: Alert):
        """Store alert in database"""
        try:
            with self.engine.connect() as conn:
                query = """
                INSERT INTO alerts (id, type, severity, title, description, timestamp, metadata, resolved)
                VALUES (:id, :type, :severity, :title, :description, :timestamp, :metadata, :resolved)
                """
                
                conn.execute(text(query), {
                    "id": alert.id,
                    "type": alert.type.value,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "description": alert.description,
                    "timestamp": alert.timestamp,
                    "metadata": json.dumps(alert.metadata),
                    "resolved": alert.resolved
                })
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")

async def main():
    """Main function to run the alerting system"""
    alerting_system = AlertingSystem()
    
    # Run monitoring every 5 minutes
    while True:
        await alerting_system.run_monitoring_cycle()
        await asyncio.sleep(300)  # 5 minutes

if __name__ == "__main__":
    asyncio.run(main())
