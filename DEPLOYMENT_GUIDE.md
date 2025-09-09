# Deployment Guide

## Infrastructure Requirements

### Hardware Specifications

#### Minimum Requirements (Development/Testing)
- **CPU**: 4 cores per VM
- **RAM**: 8GB per VM  
- **Storage**: 100GB SSD per VM
- **Network**: 1Gbps connectivity

#### Production Requirements
- **CPU**: 8+ cores per VM
- **RAM**: 16GB+ per VM
- **Storage**: 500GB+ SSD per VM (with RAID for data nodes)
- **Network**: 10Gbps connectivity with redundancy

### Network Architecture

```
[Internet] --> [Load Balancer] --> [API Gateway] --> [Microservices]
                                                  --> [Data Layer]
```

#### Network Segmentation
- **DMZ**: Load balancers and API gateways
- **Application Tier**: Microservices (private network)
- **Data Tier**: Databases and storage (isolated network)
- **Management**: Monitoring and admin access

## VM Deployment Architecture

### Datacenter 1 (Primary)

#### VM-DC1-APP-01 (Application Services)
```yaml
Role: Primary Application Server
Services:
  - Auth Service (Port: 8001)
  - Policy Service (Port: 8002)
  - HAProxy Load Balancer (Port: 80, 443)
Resources:
  CPU: 8 cores
  RAM: 16GB
  Storage: 200GB SSD
```

#### VM-DC1-APP-02 (Application Services)
```yaml
Role: Secondary Application Server  
Services:
  - Project Service (Port: 8003)
  - Secret Service (Port: 8004)
  - Audit Service (Port: 8005)
Resources:
  CPU: 8 cores
  RAM: 16GB
  Storage: 200GB SSD
```

#### VM-DC1-DATA-01 (Data Services)
```yaml
Role: Primary Data Server
Services:
  - etcd (Port: 2379, 2380)
  - Redis (Port: 6379)
  - Prometheus (Port: 9090)
Resources:
  CPU: 8 cores
  RAM: 32GB
  Storage: 1TB SSD (RAID 1)
```

#### VM-DC1-DATA-02 (Secure Storage)
```yaml
Role: Secure Storage Server
Services:
  - HashiCorp Vault (Port: 8200)
  - MinIO Object Storage (Port: 9000)
Resources:
  CPU: 4 cores
  RAM: 16GB
  Storage: 2TB SSD (RAID 1)
```

### Datacenter 2 (Secondary)

#### VM-DC2-APP-01, VM-DC2-APP-02, VM-DC2-DATA-01, VM-DC2-DATA-02
Mirror configuration of Datacenter 1 for high availability.

## Installation Steps

### 1. Base System Preparation

#### Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip
```

#### Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

#### Install Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Network Configuration

#### Firewall Rules
```bash
# Allow SSH
sudo ufw allow 22

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow inter-service communication
sudo ufw allow from 10.0.0.0/8 to any port 2379  # etcd
sudo ufw allow from 10.0.0.0/8 to any port 8200  # Vault
sudo ufw allow from 10.0.0.0/8 to any port 6379  # Redis

# Enable firewall
sudo ufw --force enable
```

#### Network Interfaces
```bash
# Configure static IP (example for Ubuntu)
sudo nano /etc/netplan/00-installer-config.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 10.0.1.10/24
      gateway4: 10.0.1.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
```

### 3. SSL Certificate Setup

#### Generate Self-Signed Certificates (Development)
```bash
mkdir -p /opt/cms/certs
cd /opt/cms/certs

# Generate CA
openssl genrsa -out ca-key.pem 4096
openssl req -new -x509 -days 365 -key ca-key.pem -sha256 -out ca.pem

# Generate server certificate
openssl genrsa -out server-key.pem 4096
openssl req -subj "/CN=cms.yourdomain.com" -sha256 -new -key server-key.pem -out server.csr
openssl x509 -req -days 365 -sha256 -in server.csr -CA ca.pem -CAkey ca-key.pem -out server-cert.pem
```

#### Let's Encrypt (Production)
```bash
sudo apt install certbot
sudo certbot certonly --standalone -d cms.yourdomain.com
```

### 4. etcd Cluster Setup

#### Create etcd Configuration
```bash
mkdir -p /opt/cms/etcd
cd /opt/cms/etcd
```

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  etcd1:
    image: quay.io/coreos/etcd:v3.5.9
    container_name: etcd1
    command:
      - /usr/local/bin/etcd
      - --name=etcd1
      - --data-dir=/etcd-data
      - --listen-client-urls=http://0.0.0.0:2379
      - --advertise-client-urls=http://10.0.1.10:2379
      - --listen-peer-urls=http://0.0.0.0:2380
      - --initial-advertise-peer-urls=http://10.0.1.10:2380
      - --initial-cluster=etcd1=http://10.0.1.10:2380,etcd2=http://10.0.2.10:2380
      - --initial-cluster-token=cms-cluster
      - --initial-cluster-state=new
    ports:
      - "2379:2379"
      - "2380:2380"
    volumes:
      - etcd-data:/etcd-data
    networks:
      - cms-network

volumes:
  etcd-data:

networks:
  cms-network:
    driver: bridge
```

#### Start etcd
```bash
docker-compose up -d
```

### 5. HashiCorp Vault Setup

#### Create Vault Configuration
```bash
mkdir -p /opt/cms/vault
cd /opt/cms/vault
```

Create `vault.hcl`:
```hcl
storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/server-cert.pem"
  tls_key_file = "/vault/certs/server-key.pem"
}

api_addr = "https://10.0.1.11:8200"
cluster_addr = "https://10.0.1.11:8201"
ui = true
```

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  vault:
    image: vault:1.14
    container_name: vault
    cap_add:
      - IPC_LOCK
    environment:
      VAULT_CONFIG_DIR: /vault/config
    command: vault server -config=/vault/config/vault.hcl
    ports:
      - "8200:8200"
    volumes:
      - ./vault.hcl:/vault/config/vault.hcl
      - vault-data:/vault/data
      - /opt/cms/certs:/vault/certs
    networks:
      - cms-network

volumes:
  vault-data:

networks:
  cms-network:
    external: true
```

#### Initialize Vault
```bash
docker-compose up -d

# Initialize Vault
export VAULT_ADDR='https://10.0.1.11:8200'
export VAULT_SKIP_VERIFY=true  # Only for self-signed certs

vault operator init -key-shares=5 -key-threshold=3 > vault-keys.txt
vault operator unseal  # (Run 3 times with different keys)

# Login with root token
vault auth $(grep 'Initial Root Token:' vault-keys.txt | awk '{print $NF}')

# Enable KV secrets engine
vault secrets enable -path=cms kv-v2
```

### 6. Redis Setup

#### Create Redis Configuration
```bash
mkdir -p /opt/cms/redis
cd /opt/cms/redis
```

Create `redis.conf`:
```
bind 0.0.0.0
port 6379
requirepass your_redis_password
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: redis
    command: redis-server /usr/local/etc/redis/redis.conf
    ports:
      - "6379:6379"
    volumes:
      - ./redis.conf:/usr/local/etc/redis/redis.conf
      - redis-data:/data
    networks:
      - cms-network

volumes:
  redis-data:

networks:
  cms-network:
    external: true
```

### 7. Microservices Deployment

#### Create Application Directory
```bash
mkdir -p /opt/cms/app
cd /opt/cms/app
```

#### Create Environment Configuration
Create `.env`:
```env
# Database Configuration
ETCD_HOSTS=10.0.1.10:2379,10.0.2.10:2379
REDIS_URL=redis://:your_redis_password@10.0.1.10:6379/0
VAULT_ADDR=https://10.0.1.11:8200
VAULT_TOKEN=your_vault_token

# Security Configuration
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Service Configuration
AUTH_SERVICE_PORT=8001
POLICY_SERVICE_PORT=8002
PROJECT_SERVICE_PORT=8003
SECRET_SERVICE_PORT=8004
AUDIT_SERVICE_PORT=8005

# External Services
GIT_REPOSITORY_URL=https://gitlab.com/your-org/policies.git
GIT_TOKEN=your_git_token

# Monitoring
PROMETHEUS_URL=http://10.0.1.10:9090
LOG_LEVEL=INFO
```

#### Create Main Docker Compose
Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  auth-service:
    image: cms/auth-service:latest
    container_name: auth-service
    ports:
      - "8001:8001"
    environment:
      - SERVICE_PORT=8001
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    networks:
      - cms-network
    depends_on:
      - redis
    restart: unless-stopped

  policy-service:
    image: cms/policy-service:latest
    container_name: policy-service
    ports:
      - "8002:8002"
    environment:
      - SERVICE_PORT=8002
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    networks:
      - cms-network
    depends_on:
      - etcd
    restart: unless-stopped

  project-service:
    image: cms/project-service:latest
    container_name: project-service
    ports:
      - "8003:8003"
    environment:
      - SERVICE_PORT=8003
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    networks:
      - cms-network
    depends_on:
      - etcd
    restart: unless-stopped

  secret-service:
    image: cms/secret-service:latest
    container_name: secret-service
    ports:
      - "8004:8004"
    environment:
      - SERVICE_PORT=8004
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    networks:
      - cms-network
    depends_on:
      - vault
    restart: unless-stopped

  audit-service:
    image: cms/audit-service:latest
    container_name: audit-service
    ports:
      - "8005:8005"
    environment:
      - SERVICE_PORT=8005
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    networks:
      - cms-network
    depends_on:
      - etcd
    restart: unless-stopped

networks:
  cms-network:
    external: true
```

### 8. Load Balancer Setup (HAProxy)

#### Create HAProxy Configuration
```bash
mkdir -p /opt/cms/haproxy
cd /opt/cms/haproxy
```

Create `haproxy.cfg`:
```
global
    daemon
    maxconn 4096
    log stdout local0
    
defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    option httplog
    
frontend cms_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/cms.pem
    redirect scheme https if !{ ssl_fc }
    
    # API routing
    acl auth_api path_beg /api/v1/auth
    acl policy_api path_beg /api/v1/policies
    acl project_api path_beg /api/v1/projects
    acl secret_api path_beg /api/v1/secrets
    acl audit_api path_beg /api/v1/audit
    acl health_api path_beg /api/v1/health
    
    use_backend auth_backend if auth_api
    use_backend policy_backend if policy_api
    use_backend project_backend if project_api
    use_backend secret_backend if secret_api
    use_backend audit_backend if audit_api
    use_backend health_backend if health_api
    
backend auth_backend
    balance roundrobin
    server auth1 10.0.1.10:8001 check
    server auth2 10.0.2.10:8001 check backup
    
backend policy_backend
    balance roundrobin
    server policy1 10.0.1.10:8002 check
    server policy2 10.0.2.10:8002 check backup
    
backend project_backend
    balance roundrobin
    server project1 10.0.1.10:8003 check
    server project2 10.0.2.10:8003 check backup
    
backend secret_backend
    balance roundrobin
    server secret1 10.0.1.10:8004 check
    server secret2 10.0.2.10:8004 check backup
    
backend audit_backend
    balance roundrobin
    server audit1 10.0.1.10:8005 check
    server audit2 10.0.2.10:8005 check backup
    
backend health_backend
    balance roundrobin
    server health1 10.0.1.10:8001 check
    server health2 10.0.2.10:8001 check backup
    
listen stats
    bind *:8404
    stats enable
    stats uri /stats
    stats refresh 30s
```

### 9. Monitoring Setup

#### Prometheus Configuration
```bash
mkdir -p /opt/cms/monitoring
cd /opt/cms/monitoring
```

Create `prometheus.yml`:
```yaml
global:
  scrape_interval: 15s
  
scrape_configs:
  - job_name: 'cms-services'
    static_configs:
      - targets: 
        - '10.0.1.10:8001'  # auth-service
        - '10.0.1.10:8002'  # policy-service
        - '10.0.1.10:8003'  # project-service
        - '10.0.1.10:8004'  # secret-service
        - '10.0.1.10:8005'  # audit-service
        
  - job_name: 'infrastructure'
    static_configs:
      - targets:
        - '10.0.1.10:2379'  # etcd
        - '10.0.1.11:8200'  # vault
        - '10.0.1.10:6379'  # redis
```

### 10. Backup Configuration

#### Create Backup Scripts
```bash
mkdir -p /opt/cms/backup
cd /opt/cms/backup
```

Create `backup.sh`:
```bash
#!/bin/bash

BACKUP_DIR="/opt/cms/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup etcd
etcdctl snapshot save $BACKUP_DIR/etcd_snapshot.db

# Backup Vault (if unsealed)
vault operator raft snapshot save $BACKUP_DIR/vault_snapshot.snap

# Backup Redis
redis-cli --rdb $BACKUP_DIR/redis_dump.rdb

# Backup configuration files
cp -r /opt/cms/app/.env $BACKUP_DIR/
cp -r /opt/cms/haproxy/haproxy.cfg $BACKUP_DIR/

# Upload to object storage
aws s3 cp $BACKUP_DIR s3://cms-backups/$(basename $BACKUP_DIR) --recursive

echo "Backup completed: $BACKUP_DIR"
```

#### Setup Cron Job
```bash
# Add to crontab
crontab -e

# Backup every 4 hours
0 */4 * * * /opt/cms/backup/backup.sh

# Daily cleanup (keep 7 days)
0 2 * * * find /opt/cms/backup -type d -mtime +7 -exec rm -rf {} \;
```

## Testing Deployment

### Health Checks
```bash
# Test individual services
curl -k https://10.0.1.10:8001/api/v1/health/
curl -k https://10.0.1.10:8002/api/v1/health/
curl -k https://10.0.1.10:8003/api/v1/health/
curl -k https://10.0.1.10:8004/api/v1/health/
curl -k https://10.0.1.10:8005/api/v1/health/

# Test load balancer
curl -k https://cms.yourdomain.com/api/v1/health/
```

### Functional Tests
```bash
# Test authentication
curl -X POST https://cms.yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Test policy listing (with auth token)
curl -H "Authorization: Bearer <token>" \
  https://cms.yourdomain.com/api/v1/policies/
```

## Security Hardening

### System Hardening
```bash
# Disable unused services
sudo systemctl disable apache2
sudo systemctl disable postfix

# Configure fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# Update SSH configuration
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no, PasswordAuthentication no
```

### Docker Security
```bash
# Run containers as non-root user
# Enable Docker content trust
export DOCKER_CONTENT_TRUST=1

# Scan images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image cms/auth-service:latest
```

## Maintenance Procedures

### Regular Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Docker images
docker-compose pull
docker-compose up -d

# Update certificates
certbot renew
```

### Log Rotation
```bash
# Configure logrotate
sudo nano /etc/logrotate.d/cms

# Add configuration
/opt/cms/app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    copytruncate
    notifempty
}
```

This deployment guide provides a comprehensive setup for a production-grade CMS system with high availability, security, and monitoring capabilities.
