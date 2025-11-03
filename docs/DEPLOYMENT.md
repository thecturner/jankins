# Deployment Guide

Comprehensive deployment guide for jankins in various environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Systemd Service](#systemd-service)
- [Cloud Deployments](#cloud-deployments)
- [Configuration Management](#configuration-management)
- [Security Hardening](#security-hardening)
- [Monitoring Setup](#monitoring-setup)

## Prerequisites

- Python 3.10+ (for source/pip deployment)
- Docker (for container deployment)
- Kubernetes cluster (for K8s deployment)
- Jenkins instance with API access
- Jenkins API token

## Deployment Options

| Method | Use Case | Pros | Cons |
|--------|----------|------|------|
| pip install | Development, testing | Simple, fast | Manual dependency management |
| Docker | Production, consistency | Isolated, reproducible | Requires Docker |
| Kubernetes | Scale, HA | Auto-scaling, resilient | Complex setup |
| Systemd | Traditional Linux | Native integration | Manual updates |

## Docker Deployment

### Using Official Image

```bash
# Pull image
docker pull jankins:latest

# Run with environment variables
docker run -d \
  --name jankins \
  -p 8080:8080 \
  -e JENKINS_URL=https://jenkins.example.com \
  -e JENKINS_USER=myuser \
  -e JENKINS_API_TOKEN=$TOKEN \
  --restart unless-stopped \
  jankins:latest
```

### Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  jankins:
    image: jankins:latest
    container_name: jankins
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      JENKINS_URL: https://jenkins.example.com
      JENKINS_USER: myuser
      JENKINS_API_TOKEN: ${JENKINS_API_TOKEN}
      MCP_TRANSPORT: http
      LOG_LEVEL: INFO
      LOG_JSON: "true"
    volumes:
      - ./logs:/var/log/jankins
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/_health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

```bash
# Deploy
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Building Custom Image

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy application
COPY src/ ./src/

# Create non-root user
RUN useradd -m -u 1000 jankins && \
    chown -R jankins:jankins /app

USER jankins

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8080/_health || exit 1

CMD ["jankins", "--transport", "http", "--bind", "0.0.0.0:8080"]
```

```bash
# Build
docker build -t jankins:custom .

# Run
docker run -d jankins:custom
```

## Kubernetes Deployment

### Namespace and ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: jankins

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: jankins-config
  namespace: jankins
data:
  MCP_TRANSPORT: "http"
  LOG_LEVEL: "INFO"
  LOG_JSON: "true"
```

### Secret for Credentials

```bash
# Create secret
kubectl create secret generic jankins-secret \
  --from-literal=jenkins-url=https://jenkins.example.com \
  --from-literal=jenkins-user=myuser \
  --from-literal=jenkins-api-token=$TOKEN \
  -n jankins
```

### Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jankins
  namespace: jankins
  labels:
    app: jankins
spec:
  replicas: 3
  selector:
    matchLabels:
      app: jankins
  template:
    metadata:
      labels:
        app: jankins
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/_metrics"
    spec:
      containers:
      - name: jankins
        image: jankins:latest
        ports:
        - containerPort: 8080
          name: http
        env:
        - name: JENKINS_URL
          valueFrom:
            secretKeyRef:
              name: jankins-secret
              key: jenkins-url
        - name: JENKINS_USER
          valueFrom:
            secretKeyRef:
              name: jankins-secret
              key: jenkins-user
        - name: JENKINS_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: jankins-secret
              key: jenkins-api-token
        envFrom:
        - configMapRef:
            name: jankins-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /_health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /_ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
```

### Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: jankins
  namespace: jankins
  labels:
    app: jankins
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
    name: http
  selector:
    app: jankins
```

### Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: jankins
  namespace: jankins
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - jankins.example.com
    secretName: jankins-tls
  rules:
  - host: jankins.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: jankins
            port:
              number: 80
```

### HPA (Horizontal Pod Autoscaler)

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: jankins
  namespace: jankins
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: jankins
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
kubectl apply -f hpa.yaml

# Check status
kubectl get all -n jankins

# View logs
kubectl logs -f deployment/jankins -n jankins

# Test service
kubectl port-forward svc/jankins 8080:80 -n jankins
curl http://localhost:8080/_health
```

## Systemd Service

### Service File

```ini
# /etc/systemd/system/jankins.service
[Unit]
Description=jankins MCP Server
After=network.target

[Service]
Type=simple
User=jankins
Group=jankins
WorkingDirectory=/opt/jankins
Environment="JENKINS_URL=https://jenkins.example.com"
Environment="JENKINS_USER=myuser"
EnvironmentFile=/etc/jankins/credentials
ExecStart=/opt/jankins/venv/bin/jankins --transport http --bind 0.0.0.0:8080
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=jankins

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/jankins

# Resource limits
MemoryLimit=1G
CPUQuota=100%

[Install]
WantedBy=multi-user.target
```

### Credentials File

```bash
# /etc/jankins/credentials
JENKINS_API_TOKEN=your-token-here
```

### Setup

```bash
# Create user
sudo useradd -r -s /bin/false jankins

# Create directories
sudo mkdir -p /opt/jankins /var/log/jankins /etc/jankins
sudo chown jankins:jankins /var/log/jankins

# Install jankins
sudo -u jankins python3 -m venv /opt/jankins/venv
sudo -u jankins /opt/jankins/venv/bin/pip install jankins

# Set up credentials
sudo vim /etc/jankins/credentials
sudo chmod 600 /etc/jankins/credentials
sudo chown jankins:jankins /etc/jankins/credentials

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable jankins
sudo systemctl start jankins

# Check status
sudo systemctl status jankins
sudo journalctl -u jankins -f
```

## Cloud Deployments

### AWS ECS

```json
{
  "family": "jankins",
  "containerDefinitions": [
    {
      "name": "jankins",
      "image": "jankins:latest",
      "memory": 512,
      "cpu": 256,
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "MCP_TRANSPORT", "value": "http"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "secrets": [
        {
          "name": "JENKINS_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:jankins-ABCD:jenkins_url::"
        },
        {
          "name": "JENKINS_USER",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:jankins-ABCD:jenkins_user::"
        },
        {
          "name": "JENKINS_API_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:jankins-ABCD:jenkins_token::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/jankins",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "jankins"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/_health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

### Google Cloud Run

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/jankins

# Deploy
gcloud run deploy jankins \
  --image gcr.io/PROJECT_ID/jankins \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars JENKINS_URL=https://jenkins.example.com \
  --set-env-vars JENKINS_USER=myuser \
  --set-secrets JENKINS_API_TOKEN=jankins-token:latest
```

## Configuration Management

### Using Ansible

```yaml
# playbook.yml
---
- name: Deploy jankins
  hosts: jankins_servers
  become: yes
  tasks:
    - name: Install jankins
      pip:
        name: jankins
        state: present

    - name: Create jankins user
      user:
        name: jankins
        system: yes
        shell: /bin/false

    - name: Create systemd service
      template:
        src: jankins.service.j2
        dest: /etc/systemd/system/jankins.service
      notify: reload systemd

    - name: Create credentials file
      template:
        src: credentials.j2
        dest: /etc/jankins/credentials
        mode: '0600'
        owner: jankins

    - name: Start jankins service
      systemd:
        name: jankins
        state: started
        enabled: yes

  handlers:
    - name: reload systemd
      systemd:
        daemon_reload: yes
```

## Security Hardening

### 1. Network Security

```bash
# Firewall rules (iptables)
sudo iptables -A INPUT -p tcp --dport 8080 -s 10.0.0.0/8 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8080 -j DROP

# Or using ufw
sudo ufw allow from 10.0.0.0/8 to any port 8080
sudo ufw enable
```

### 2. TLS/SSL

Use reverse proxy (nginx) for TLS:

```nginx
# /etc/nginx/sites-available/jankins
server {
    listen 443 ssl http2;
    server_name jankins.example.com;

    ssl_certificate /etc/letsencrypt/live/jankins.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jankins.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. Secrets Management

Use HashiCorp Vault:

```bash
# Store secret
vault kv put secret/jankins \
  jenkins_url=https://jenkins.example.com \
  jenkins_user=myuser \
  jenkins_token=secret123

# Retrieve in script
export JENKINS_API_TOKEN=$(vault kv get -field=jenkins_token secret/jankins)
```

## Monitoring Setup

See [MONITORING.md](./MONITORING.md) for complete monitoring setup.

Quick setup:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'jankins'
    static_configs:
      - targets: ['jankins:8080']
    metrics_path: '/_metrics'
```

## Troubleshooting

See [RUNBOOKS.md](./RUNBOOKS.md) for operational runbooks.

## Next Steps

- Set up [Monitoring](./MONITORING.md)
- Review [Security Policy](../SECURITY.md)
- Configure [Alerting](./MONITORING.md#alerting)
- Test [Disaster Recovery](#disaster-recovery)
