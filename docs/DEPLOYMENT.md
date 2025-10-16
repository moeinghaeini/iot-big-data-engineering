# Deployment Guide

## Overview

This guide covers deploying the IoT Big Data Engineering project in various environments, from local development to production.

## Prerequisites

- Docker and Docker Compose
- Kubernetes cluster (for production)
- Git
- Basic knowledge of containerization and orchestration

## Local Development

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/moeinghaeini/iot-big-data-engineering.git
   cd iot-big-data-engineering
   ```

2. **Start the infrastructure**
   ```bash
   docker-compose up -d
   ```

3. **Wait for services to be ready**
   ```bash
   # Check service status
   docker-compose ps
   
   # Check logs
   docker-compose logs -f
   ```

4. **Access the services**
   - API Documentation: http://localhost:8000/docs
   - Grafana Dashboard: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090
   - Spark Master: http://localhost:8080
   - HDFS NameNode: http://localhost:9870

### Development Setup

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Scala/SBT**
   ```bash
   # macOS
   brew install sbt
   
   # Ubuntu
   echo "deb https://repo.scala-sbt.org/scalasbt/debian all main" | sudo tee /etc/apt/sources.list.d/sbt.list
   sudo apt-key adv --keyserver hnp://keyserver.ubuntu.com:80 --recv 642AC823
   sudo apt-get update
   sudo apt-get install sbt
   ```

3. **Run tests**
   ```bash
   # Python tests
   pytest tests/
   
   # Scala tests
   sbt test
   ```

## Docker Deployment

### Building Images

```bash
# Build API image
docker build -f docker/Dockerfile.api -t sensor-api:latest .

# Build data generator image
docker build -f docker/Dockerfile.data-generator -t sensor-data-generator:latest .
```

### Running with Docker Compose

```bash
# Start all services
docker-compose up -d

# Scale specific services
docker-compose up -d --scale data-generator=3

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Environment Variables

Create a `.env` file for custom configuration:

```env
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/sensor_data

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC=sensor-data

# API
API_HOST=0.0.0.0
API_PORT=8000

# Monitoring
PROMETHEUS_RETENTION=200h
GRAFANA_ADMIN_PASSWORD=secure_password
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm (optional, for easier deployment)

### Using Helm (Recommended)

1. **Create Helm chart**
   ```bash
   helm create sensor-pipeline
   cd sensor-pipeline
   ```

2. **Update values.yaml**
   ```yaml
   replicaCount: 3
   
   image:
     repository: ghcr.io/moeinghaeini/iot-big-data-engineering
     tag: latest
     pullPolicy: IfNotPresent
   
   service:
     type: ClusterIP
     port: 8000
   
   ingress:
     enabled: true
     className: nginx
     annotations:
       cert-manager.io/cluster-issuer: letsencrypt-prod
     hosts:
       - host: sensor-api.example.com
         paths:
           - path: /
             pathType: Prefix
     tls:
       - secretName: sensor-api-tls
         hosts:
           - sensor-api.example.com
   
   resources:
     limits:
       cpu: 1000m
       memory: 1Gi
     requests:
       cpu: 500m
       memory: 512Mi
   
   autoscaling:
     enabled: true
     minReplicas: 2
     maxReplicas: 10
     targetCPUUtilizationPercentage: 70
   ```

3. **Deploy with Helm**
   ```bash
   helm install sensor-pipeline ./sensor-pipeline
   ```

### Manual Kubernetes Deployment

1. **Create namespace**
   ```bash
   kubectl create namespace sensor-pipeline
   ```

2. **Deploy PostgreSQL**
   ```bash
   kubectl apply -f k8s/postgres.yaml
   ```

3. **Deploy Kafka**
   ```bash
   kubectl apply -f k8s/kafka.yaml
   ```

4. **Deploy API service**
   ```bash
   kubectl apply -f k8s/api.yaml
   ```

5. **Deploy monitoring**
   ```bash
   kubectl apply -f k8s/monitoring.yaml
   ```

### Kubernetes Manifests

#### API Deployment (k8s/api.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sensor-api
  namespace: sensor-pipeline
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sensor-api
  template:
    metadata:
      labels:
        app: sensor-api
    spec:
      containers:
      - name: api
        image: ghcr.io/moeinghaeini/iot-big-data-engineering/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: sensor-secrets
              key: database-url
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka:9092"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: sensor-api
  namespace: sensor-pipeline
spec:
  selector:
    app: sensor-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

## Production Considerations

### Security

1. **Use secrets for sensitive data**
   ```bash
   kubectl create secret generic sensor-secrets \
     --from-literal=database-url=postgresql://user:password@postgres:5432/sensor_data \
     --from-literal=kafka-password=secure_password
   ```

2. **Enable TLS/SSL**
   - Use cert-manager for automatic certificate management
   - Configure ingress with TLS termination

3. **Network policies**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: sensor-api-netpol
   spec:
     podSelector:
       matchLabels:
         app: sensor-api
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: ingress-nginx
     egress:
     - to:
       - namespaceSelector:
           matchLabels:
             name: sensor-pipeline
   ```

### Monitoring and Observability

1. **Prometheus monitoring**
   ```bash
   # Install Prometheus operator
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack
   ```

2. **Log aggregation**
   ```bash
   # Install ELK stack
   helm repo add elastic https://helm.elastic.co
   helm install elasticsearch elastic/elasticsearch
   helm install kibana elastic/kibana
   helm install logstash elastic/logstash
   ```

3. **Distributed tracing**
   ```bash
   # Install Jaeger
   helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
   helm install jaeger jaegertracing/jaeger
   ```

### Performance Optimization

1. **Resource limits and requests**
   ```yaml
   resources:
     requests:
       memory: "512Mi"
       cpu: "500m"
     limits:
       memory: "1Gi"
       cpu: "1000m"
   ```

2. **Horizontal Pod Autoscaling**
   ```yaml
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: sensor-api-hpa
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: sensor-api
     minReplicas: 2
     maxReplicas: 10
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70
   ```

3. **Database optimization**
   - Use connection pooling
   - Implement read replicas
   - Configure appropriate indexes

### Backup and Disaster Recovery

1. **Database backups**
   ```bash
   # Automated PostgreSQL backups
   kubectl create cronjob postgres-backup \
     --image=postgres:15 \
     --schedule="0 2 * * *" \
     -- pg_dump -h postgres -U user sensor_data > /backup/sensor_data_$(date +%Y%m%d).sql
   ```

2. **Configuration backups**
   ```bash
   # Backup Kubernetes configurations
   kubectl get all -n sensor-pipeline -o yaml > sensor-pipeline-backup.yaml
   ```

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check pod status
   kubectl get pods -n sensor-pipeline
   
   # Check logs
   kubectl logs -f deployment/sensor-api -n sensor-pipeline
   ```

2. **Database connection issues**
   ```bash
   # Test database connectivity
   kubectl exec -it deployment/postgres -n sensor-pipeline -- psql -U user -d sensor_data -c "SELECT 1;"
   ```

3. **Kafka connectivity issues**
   ```bash
   # Check Kafka topics
   kubectl exec -it deployment/kafka -n sensor-pipeline -- kafka-topics --list --bootstrap-server localhost:9092
   ```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
kubectl exec -it deployment/postgres -n sensor-pipeline -- pg_isready

# Kafka health
kubectl exec -it deployment/kafka -n sensor-pipeline -- kafka-broker-api-versions --bootstrap-server localhost:9092
```

## Scaling

### Horizontal Scaling

```bash
# Scale API replicas
kubectl scale deployment sensor-api --replicas=5 -n sensor-pipeline

# Scale data generators
kubectl scale deployment data-generator --replicas=10 -n sensor-pipeline
```

### Vertical Scaling

```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "1000m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## Maintenance

### Updates

1. **Rolling updates**
   ```bash
   kubectl set image deployment/sensor-api api=ghcr.io/moeinghaeini/iot-big-data-engineering/api:v2.0.0 -n sensor-pipeline
   ```

2. **Database migrations**
   ```bash
   kubectl exec -it deployment/sensor-api -n sensor-pipeline -- alembic upgrade head
   ```

### Monitoring

- Set up alerts for critical metrics
- Monitor resource usage
- Track application performance
- Monitor data quality metrics
