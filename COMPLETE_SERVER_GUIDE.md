# 🏥 REFORMMED Monitor — Complete Server Documentation

**Version:** 1.0  
**Last Updated:** February 18, 2026  
**Server IP:** 164.52.221.241

---

## 📋 Table of Contents

1. [System Overview](#-system-overview)
2. [Architecture](#-architecture)
3. [Server Credentials](#-server-credentials)
4. [Initial Setup & Installation](#-initial-setup--installation)
5. [Docker Stack Management](#-docker-stack-management)
6. [Database Operations](#-database-operations)
7. [Machine Management](#-machine-management)
8. [Agent Installation](#-agent-installation)
9. [Grafana Dashboards](#-grafana-dashboards)
10. [Email Alerts](#-email-alerts)
11. [API Reference](#-api-reference)
12. [Monitoring & Logs](#-monitoring--logs)
13. [Troubleshooting](#-troubleshooting)
14. [Backup & Recovery](#-backup--recovery)
15. [Security](#-security)
16. [Performance Tuning](#-performance-tuning)
17. [Upgrade & Maintenance](#-upgrade--maintenance)
18. [Complete Command Reference](#-complete-command-reference)
19. [Change Log](#-change-log)

---

## 🎯 System Overview

REFORMMED Monitor is a real-time infrastructure monitoring system designed for healthcare facilities. It collects system metrics every second from multiple machines (Windows/Linux) and displays them in Grafana dashboards with automated alerting.

### Key Features
- ✅ Real-time monitoring (1-second intervals)
- ✅ Auto-dashboard creation for new machines
- ✅ Email alerts for offline/threshold breaches
- ✅ Multi-platform support (Windows, Ubuntu, Linux)
- ✅ GPU monitoring (NVIDIA, Intel iGPU, AMD)
- ✅ Zero-configuration agent deployment
- ✅ Historical data retention
- ✅ RESTful API access

### Metrics Collected
- CPU usage (total + per-core) + frequency + temperature
- RAM & Swap usage
- GPU usage, VRAM, temperature (auto-detects NVIDIA/Intel/AMD)
- Disk usage per partition (excludes snap/loop devices)
- Network traffic (bytes in/out per second)
- Top 10 processes by CPU
- System uptime, hostname, OS version, public IP

---

## 🏗 Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Client Machines                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Ubuntu Agent │  │Windows Agent │  │Windows Agent │     │
│  │ (systemd)    │  │ (Task Sched) │  │ (Task Sched) │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │ Metrics every 1s                │
└────────────────────────────┼─────────────────────────────────┘
                             ▼
                  HTTP POST /metrics
                             │
┌────────────────────────────┼─────────────────────────────────┐
│              VM Server (164.52.221.241)                      │
│                            ▼                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI (port 8000)                                 │   │
│  │  - /register  - /metrics  - /machines                │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │ Store metrics                     │
│                          ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  PostgreSQL (port 5432)                              │   │
│  │  - machine_registry (tracks all machines)            │   │
│  │  - machine_* tables (1 per machine, timeseries)      │   │
│  └──────┬───────────────────────────┬───────────────────┘   │
│         │                            │                        │
│         │                            │                        │
│    ┌────▼─────┐              ┌──────▼──────┐                │
│    │ Checker  │              │ Dashboard   │                │
│    │ (alerts) │              │ Manager     │                │
│    └────┬─────┘              └──────┬──────┘                │
│         │                            │                        │
│         │ Email alerts               │ Auto-create           │
│         ▼                            ▼                        │
│    Gmail SMTP                  Grafana API                   │
│                                      │                        │
│                          ┌───────────▼──────────┐            │
│                          │  Grafana (port 3000) │            │
│                          │  - Fleet dashboard   │            │
│                          │  - Per-machine dash  │            │
│                          └──────────────────────┘            │
└──────────────────────────────────────────────────────────────┘
```

### Technology Stack
| Component | Technology | Port | Purpose |
|---|---|---|---|
| **API Server** | FastAPI (Python) | 8000 | Receive metrics from agents |
| **Database** | PostgreSQL 16 | 5432 | Store timeseries data |
| **Dashboards** | Grafana 11.2.0 | 3000 | Visualize metrics |
| **Alert Engine** | Python (SMTP) | - | Send email alerts |
| **Dashboard Manager** | Python (Grafana API) | - | Auto-create dashboards |
| **Container Runtime** | Docker Compose | - | Orchestrate services |

---

## 🔐 Server Credentials

### VM Access
```
SSH: root@164.52.221.241
```

### Grafana
```
URL:      http://164.52.221.241:3000
Username: admin
Password: monitor2345
```

### PostgreSQL
```
Host:     164.52.221.241
Port:     5432
Database: monitor_machine
Username: reformmed
Password: monitor2345
```

### API
```
Endpoint: http://164.52.221.241:8000
Secret:   6aec8f303a91bedf21f9362257f9f4d5cb5168b1
```

### Email (Gmail SMTP)
```
Account:      info@reformmed.ai
App Password: dhzlqwyppbywcfmj
Recipients:   info@reformmed.ai, prakash@reformmed.ai
```

### File Paths
```
Server root:  /opt/reformmed-monitor/server
Agent (Linux): /opt/reformmed-agent
Agent (Windows): C:\reformmed-agent
```

---

## 🚀 Initial Setup & Installation

### Prerequisites
- Ubuntu 24 VM with public IP
- Docker & Docker Compose installed
- Ports 8000, 3000, 5432 open in firewall
- Gmail account with App Password

### Step 1: Clone Repository
```bash
cd /opt
git clone https://github.com/vivekdummi/com.server.reformmed.monitor.git reformmed-monitor
cd reformmed-monitor/server
```

### Step 2: Create .env File
```bash
cat > .env << 'EOF'
# Database
POSTGRES_USER=reformmed
POSTGRES_PASSWORD=monitor2345
POSTGRES_DB=monitor_machine

# API
API_SECRET=6aec8f303a91bedf21f9362257f9f4d5cb5168b1

# Grafana
GRAFANA_USER=admin
GRAFANA_PASS=monitor2345

# Alerts
OFFLINE_AFTER_SECS=10
CHECK_INTERVAL_SECS=3
CPU_ALERT_THRESH=90
RAM_ALERT_THRESH=90
DISK_ALERT_THRESH=85
TEMP_ALERT_THRESH=80

# Email
GMAIL_USER=info@reformmed.ai
GMAIL_APP_PASS=dhzlqwyppbywcfmj
ALERT_TO=info@reformmed.ai,prakash@reformmed.ai
EOF
```

### Step 3: Start Services
```bash
docker compose --env-file .env up -d
```

### Step 4: Verify All Services Running
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected output:
```
NAMES                         STATUS          PORTS
reformmed_dashboard_manager   Up 10 seconds
reformmed_checker             Up 10 seconds
reformmed_api                 Up 10 seconds   0.0.0.0:8000->8000/tcp
reformmed_grafana             Up 15 seconds   0.0.0.0:3000->3000/tcp
reformmed_postgres            Up 15 seconds   0.0.0.0:5432->5432/tcp
```

### Step 5: Test API Health
```bash
curl -s http://localhost:8000/health
# Expected: {"status":"ok","time":"..."}
```

### Step 6: Access Grafana
```
Open: http://164.52.221.241:3000
Login: admin / monitor2345
```

---

## 🐳 Docker Stack Management

### View All Containers
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Start All Services
```bash
cd /opt/reformmed-monitor/server
docker compose --env-file .env up -d
```

### Stop All Services
```bash
cd /opt/reformmed-monitor/server
docker compose --env-file .env down
```

### Restart All Services
```bash
cd /opt/reformmed-monitor/server
docker compose --env-file .env restart
```

### Start/Stop/Restart Individual Containers
```bash
# API Server
docker start reformmed_api
docker stop reformmed_api
docker restart reformmed_api

# Alert Checker
docker start reformmed_checker
docker stop reformmed_checker
docker restart reformmed_checker

# Dashboard Manager
docker start reformmed_dashboard_manager
docker stop reformmed_dashboard_manager
docker restart reformmed_dashboard_manager

# Grafana
docker start reformmed_grafana
docker stop reformmed_grafana
docker restart reformmed_grafana

# PostgreSQL
docker start reformmed_postgres
docker stop reformmed_postgres
docker restart reformmed_postgres
```

### View Logs
```bash
# Last 50 lines
docker logs reformmed_api --tail 50
docker logs reformmed_checker --tail 50
docker logs reformmed_dashboard_manager --tail 50
docker logs reformmed_grafana --tail 50
docker logs reformmed_postgres --tail 50

# Follow live logs
docker logs reformmed_api -f
docker logs reformmed_checker -f
docker logs reformmed_dashboard_manager -f
```

### Rebuild After Code Changes
```bash
cd /opt/reformmed-monitor/server

# Rebuild all
docker compose --env-file .env up -d --build

# Rebuild single service
docker compose --env-file .env up -d --build api
docker compose --env-file .env up -d --build checker
docker compose --env-file .env up -d --build dashboard_manager
```

### Check Resource Usage
```bash
docker stats --no-stream
```

### Remove and Recreate Container
```bash
cd /opt/reformmed-monitor/server
docker compose --env-file .env stop dashboard_manager
docker compose --env-file .env rm -f dashboard_manager
docker compose --env-file .env up -d --build dashboard_manager
```

---

## 🗄 Database Operations

### Connect to Database
```bash
# Interactive psql
docker exec -it reformmed_postgres psql -U reformmed -d monitor_machine

# One-liner query
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "SELECT version();"
```

### List All Tables
```bash
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "\dt"
```

### View Machine Registry
```bash
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
SELECT
  id,
  system_name,
  location,
  table_name,
  status,
  public_ip,
  hostname,
  os_type,
  registered_at,
  last_seen
FROM machine_registry
ORDER BY id;
"
```

### Check Machine Status with Time
```bash
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
SELECT
  system_name,
  location,
  status,
  public_ip,
  last_seen,
  EXTRACT(EPOCH FROM NOW()-last_seen)::int AS seconds_ago
FROM machine_registry
ORDER BY system_name;
"
```

### View Latest Metrics from a Machine
```bash
# Replace TABLE_NAME with actual table e.g. machine_kangroocare_pc1_benglore
TABLE="machine_kangroocare_pc1_benglore"

docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
SELECT
  ts,
  cpu_percent,
  ram_percent,
  swap_percent,
  status,
  public_ip,
  hostname
FROM ${TABLE}
ORDER BY ts DESC
LIMIT 5;
"
```

### Count Total Rows in Machine Table
```bash
TABLE="machine_kangroocare_pc1_benglore"

docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
SELECT
  COUNT(*) AS total_rows,
  MIN(ts) AS oldest_data,
  MAX(ts) AS newest_data,
  EXTRACT(EPOCH FROM (MAX(ts) - MIN(ts)))/3600 AS hours_of_data
FROM ${TABLE};
"
```

### Check Database Size
```bash
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
SELECT
  table_name,
  pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS size
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;
"
```

### View Top Processes on a Machine
```bash
TABLE="machine_kangroocare_pc1_benglore"

docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
SELECT
  p->>'name' AS process,
  (p->>'cpu_percent')::float AS cpu_pct,
  (p->>'mem_percent')::float AS mem_pct,
  p->>'status' AS status
FROM ${TABLE}, jsonb_array_elements(top_processes) AS p
WHERE ts = (SELECT MAX(ts) FROM ${TABLE})
ORDER BY cpu_pct DESC
LIMIT 10;
"
```

### View Disk Partitions
```bash
TABLE="machine_kangroocare_pc1_benglore"

docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
SELECT
  d->>'mountpoint' AS mount,
  d->>'device' AS device,
  (d->>'total_gb')::float AS total_gb,
  (d->>'used_gb')::float AS used_gb,
  (d->>'free_gb')::float AS free_gb,
  (d->>'percent')::float AS used_pct
FROM ${TABLE}, jsonb_array_elements(disk_partitions) AS d
WHERE ts = (SELECT MAX(ts) FROM ${TABLE});
"
```

### View GPU Info
```bash
TABLE="machine_kangroocare_pc1_benglore"

docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
SELECT
  g->>'name' AS gpu_name,
  g->>'type' AS gpu_type,
  (g->>'gpu_percent')::float AS gpu_usage,
  (g->>'mem_percent')::float AS vram_usage,
  (g->>'temp_c')::float AS temp_c
FROM ${TABLE}, jsonb_array_elements(gpu_info) AS g
WHERE ts = (SELECT MAX(ts) FROM ${TABLE})
LIMIT 1;
"
```

### Delete Old Data (Retention Policy)
```bash
# Keep last 7 days
TABLE="machine_kangroocare_pc1_benglore"
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
DELETE FROM ${TABLE} WHERE ts < NOW() - INTERVAL '7 days';
"

# Keep last 30 days
TABLE="machine_kangroocare_pc1_benglore"
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
DELETE FROM ${TABLE} WHERE ts < NOW() - INTERVAL '30 days';
"

# Keep last 90 days
TABLE="machine_kangroocare_pc1_benglore"
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
DELETE FROM ${TABLE} WHERE ts < NOW() - INTERVAL '90 days';
"
```

### Vacuum Database (Free Space)
```bash
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "VACUUM ANALYZE;"
```

### Backup Database
```bash
# Full backup
docker exec reformmed_postgres pg_dump -U reformmed monitor_machine > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
docker exec reformmed_postgres pg_dump -U reformmed monitor_machine | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore Database
```bash
# From plain SQL
cat backup_20260218_120000.sql | docker exec -i reformmed_postgres psql -U reformmed -d monitor_machine

# From compressed
gunzip < backup_20260218_120000.sql.gz | docker exec -i reformmed_postgres psql -U reformmed -d monitor_machine
```

---

## 🖥 Machine Management

### List All Machines (API)
```bash
curl -s -H "X-Api-Key: 6aec8f303a91bedf21f9362257f9f4d5cb5168b1" \
  http://164.52.221.241:8000/machines | python3 -m json.tool
```

### Get Latest Metrics for a Machine
```bash
TABLE="machine_kangroocare_pc1_benglore"

curl -s -H "X-Api-Key: 6aec8f303a91bedf21f9362257f9f4d5cb5168b1" \
  "http://164.52.221.241:8000/machines/${TABLE}/latest" | python3 -m json.tool
```

### Get Historical Metrics
```bash
TABLE="machine_kangroocare_pc1_benglore"

# Last 60 minutes
curl -s -H "X-Api-Key: 6aec8f303a91bedf21f9362257f9f4d5cb5168b1" \
  "http://164.52.221.241:8000/machines/${TABLE}/history?minutes=60" | python3 -m json.tool

# Last 24 hours
curl -s -H "X-Api-Key: 6aec8f303a91bedf21f9362257f9f4d5cb5168b1" \
  "http://164.52.221.241:8000/machines/${TABLE}/history?minutes=1440" | python3 -m json.tool
```

### Remove a Specific Machine
```bash
# Stop agent on client machine first, then:
TABLE="machine_kangroocare_pc1_benglore"
NAME="Kangroocare-PC1"

docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
DROP TABLE IF EXISTS ${TABLE};
DELETE FROM machine_registry WHERE table_name='${TABLE}';
"

echo "Machine ${NAME} removed from database"
```

### Remove Machine Dashboard
```bash
# Replace UID with dashboard uid (mach-{table_name})
UID="mach-machine_kangroocare_pc1_benglore"

curl -s -u 'admin:monitor2345' \
  -X DELETE "http://localhost:3000/api/dashboards/uid/${UID}"

echo "Dashboard deleted"
```

### Mark Machine as Offline Manually
```bash
TABLE="machine_kangroocare_pc1_benglore"

docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
UPDATE machine_registry
SET status='offline'
WHERE table_name='${TABLE}';
"
```

### Remove ALL Machines (Full Wipe)
```bash
# Stop dashboard manager first
docker stop reformmed_dashboard_manager

# Drop all machine tables
docker exec reformmed_postgres psql -U reformmed -d monitor_machine << 'SQL'
DO $$
DECLARE tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name LIKE 'machine_%'
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS %I CASCADE', tbl);
        RAISE NOTICE 'Dropped: %', tbl;
    END LOOP;
END;
$$;
TRUNCATE machine_registry RESTART IDENTITY;
SELECT COUNT(*) AS machines_remaining FROM machine_registry;
SQL

# Start dashboard manager
docker start reformmed_dashboard_manager
```

---

## 🤖 Agent Installation

### Ubuntu/Linux Installation
```bash
# Download and run installer
curl -sSL https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/install-linux.sh -o /tmp/install.sh
chmod +x /tmp/install.sh
sudo bash /tmp/install.sh
```

**Prompts:**
- VM Server IP: `164.52.221.241`
- Port: `8000`
- API Secret: `6aec8f303a91bedf21f9362257f9f4d5cb5168b1`
- Machine name: e.g. `Salem-Hospital-PC1` (no spaces)
- Location: e.g. `Salem`
- Interval: `1`

### Windows Installation
```powershell
# Open PowerShell as Administrator, then:
irm https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/install-windows.ps1 | iex
```

**Prompts:** Same as Linux

### Linux Agent Management
```bash
# Status
systemctl status reformmed-agent

# View logs live
journalctl -u reformmed-agent -f

# Last 20 lines
journalctl -u reformmed-agent --no-pager -n 20

# Restart
sudo systemctl restart reformmed-agent

# Stop
sudo systemctl stop reformmed-agent

# Start
sudo systemctl start reformmed-agent

# Edit config
sudo nano /opt/reformmed-agent/.env
sudo systemctl restart reformmed-agent

# Update to latest
sudo curl -sSL https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/agent.py \
  -o /opt/reformmed-agent/agent.py
sudo systemctl restart reformmed-agent

# Remove completely
sudo systemctl stop reformmed-agent
sudo systemctl disable reformmed-agent
sudo rm -f /etc/systemd/system/reformmed-agent.service
sudo systemctl daemon-reload
sudo rm -rf /opt/reformmed-agent
```

### Windows Agent Management
```powershell
# Status
Get-ScheduledTask -TaskName 'ReformmedMonitorAgent' | Select-Object TaskName, State

# Stop
Stop-ScheduledTask -TaskName 'ReformmedMonitorAgent'

# Start
Start-ScheduledTask -TaskName 'ReformmedMonitorAgent'

# Edit config
notepad C:\reformmed-agent\.env
Stop-ScheduledTask -TaskName 'ReformmedMonitorAgent'
Start-ScheduledTask -TaskName 'ReformmedMonitorAgent'

# Update to latest
Stop-ScheduledTask -TaskName 'ReformmedMonitorAgent'
Invoke-WebRequest "https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/agent.py" `
    -OutFile "C:\reformmed-agent\agent.py" -UseBasicParsing
Start-ScheduledTask -TaskName 'ReformmedMonitorAgent'

# Remove completely
Get-ScheduledTask -TaskName 'ReformmedMonitorAgent' | Unregister-ScheduledTask -Confirm:$false
Remove-Item -Recurse -Force "C:\reformmed-agent"
```

### Agent Auto-Start on Reboot
- **Linux:** Runs as systemd service — auto-starts on every boot
- **Windows:** Runs as Scheduled Task with `AtStartup` trigger — auto-starts on every boot

---

## 📊 Grafana Dashboards

### URLs
```
Fleet Overview: http://164.52.221.241:3000/d/reformmed-fleet
Machine Pattern: http://164.52.221.241:3000/d/mach-{table_name}
Login: admin / monitor2345
```

### List All Dashboards
```bash
curl -s -u 'admin:monitor2345' \
  'http://localhost:3000/api/search?type=dash-db' | \
  python3 -c "
import sys, json
for d in json.load(sys.stdin):
    print(f'  UID: {d[\"uid\"]:45} Title: {d[\"title\"]}')
"
```

### Force Recreate All Dashboards
```bash
docker restart reformmed_dashboard_manager
sleep 20
docker logs reformmed_dashboard_manager --tail 10
```

### Delete a Specific Dashboard
```bash
UID="mach-machine_kangroocare_pc1_benglore"

curl -s -u 'admin:monitor2345' \
  -X DELETE "http://localhost:3000/api/dashboards/uid/${UID}"

echo "Dashboard deleted"
```

### Delete ALL Dashboards
```bash
python3 << 'PYEOF'
import urllib.request, base64, json

creds = base64.b64encode(b"admin:monitor2345").decode()

def gapi(path, method="GET"):
    req = urllib.request.Request(
        f"http://localhost:3000{path}", method=method,
        headers={"Content-Type":"application/json","Authorization":f"Basic {creds}"}
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except:
        return {}

dashboards = gapi("/api/search?type=dash-db&limit=100")
for d in dashboards:
    gapi(f"/api/dashboards/uid/{d['uid']}", method="DELETE")
    print(f"Deleted: {d['title']}")

print(f"Total deleted: {len(dashboards)}")
PYEOF
```

### Check Grafana Datasource Health
```bash
curl -s -u 'admin:monitor2345' \
  -X POST http://localhost:3000/api/datasources/uid/PCC52D03280B7034C/health | \
  python3 -m json.tool
```

### Change Grafana Admin Password
```bash
# Reset password
docker exec reformmed_grafana grafana-cli admin reset-admin-password NEW_PASSWORD

# Update .env
sed -i 's/GRAFANA_PASS=.*/GRAFANA_PASS=NEW_PASSWORD/' /opt/reformmed-monitor/server/.env

# Update dashboard_manager.py
sed -i 's/admin:monitor2345/admin:NEW_PASSWORD/g' /opt/reformmed-monitor/server/dashboard_manager.py

# Rebuild dashboard manager
cd /opt/reformmed-monitor/server
docker compose --env-file .env up -d --build dashboard_manager
```

### Create Additional Grafana Admin User
1. Login to http://164.52.221.241:3000
2. Go to **Administration** → **Users**
3. Click **New user**
4. Fill details (username, email, password)
5. Save user
6. Click **Edit** on new user
7. Change **Role** to **Admin**
8. Save

---

## 🔔 Email Alerts

### View Current Alert Configuration
```bash
grep -E "GMAIL|ALERT|THRESH|OFFLINE|CHECK" /opt/reformmed-monitor/server/.env
```

### Edit Alert Settings
```bash
nano /opt/reformmed-monitor/server/.env

# Then restart checker
docker restart reformmed_checker
```

### Alert Thresholds
```bash
# In /opt/reformmed-monitor/server/.env
OFFLINE_AFTER_SECS=10      # Alert if no data for 10 seconds
CHECK_INTERVAL_SECS=3      # Check every 3 seconds
CPU_ALERT_THRESH=90        # Alert if CPU > 90%
RAM_ALERT_THRESH=90        # Alert if RAM > 90%
DISK_ALERT_THRESH=85       # Alert if Disk > 85%
TEMP_ALERT_THRESH=80       # Alert if Temperature > 80°C
```

### Gmail SMTP Settings
```bash
GMAIL_USER=info@reformmed.ai
GMAIL_APP_PASS=dhzlqwyppbywcfmj
ALERT_TO=info@reformmed.ai,prakash@reformmed.ai
```

### Test Email Manually
```bash
python3 << 'PYEOF'
import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Test alert from REFORMMED Monitor - All systems operational")
msg["Subject"] = "TEST: REFORMMED Monitor Alert"
msg["From"] = "info@reformmed.ai"
msg["To"] = "info@reformmed.ai"

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login("info@reformmed.ai", "dhzlqwyppbywcfmj")
    s.sendmail("info@reformmed.ai", ["info@reformmed.ai"], msg.as_string())

print("✅ Test email sent successfully")
PYEOF
```

### Alert Types
| Alert | Trigger | Email Subject | Color |
|---|---|---|---|
| 🔴 Machine Offline | No data for 10s | 🔴 OFFLINE: {machine} ({location}) | Red |
| 🟢 Machine Online | Machine reconnects | 🟢 ONLINE: {machine} ({location}) | Green |
| ⚠️ High CPU | Above 90% | ⚠️ HIGH CPU: {machine} — {value}% | Orange |
| ⚠️ High RAM | Above 90% | ⚠️ HIGH RAM: {machine} — {value}% | Orange |
| 💾 Disk Full | Above 85% | 💾 DISK FULL: {machine} — {value}% | Purple |
| 🌡 High Temperature | Above 80°C | 🌡 HIGH TEMP: {machine} — {value}°C | Orange |

### Alert Cooldown
Each alert type has a 10-minute cooldown per machine to prevent spam.

### View Alert Checker Logs
```bash
docker logs reformmed_checker --tail 50
docker logs reformmed_checker -f
```

---

## 🔑 API Reference

### Health Check
```bash
curl -s http://164.52.221.241:8000/health
```

Response:
```json
{
  "status": "ok",
  "time": "2026-02-18T10:30:00.123456"
}
```

### List All Machines
```bash
curl -s -H "X-Api-Key: 6aec8f303a91bedf21f9362257f9f4d5cb5168b1" \
  http://164.52.221.241:8000/machines | python3 -m json.tool
```

Response:
```json
[
  {
    "id": 1,
    "system_name": "Kangroocare-PC1",
    "location": "Benglore",
    "table_name": "machine_kangroocare_pc1_benglore",
    "status": "online",
    "public_ip": "106.51.66.127",
    "hostname": "kangroo-pc",
    "os_type": "linux",
    "registered_at": "2026-02-18T05:15:30.123456Z",
    "last_seen": "2026-02-18T10:30:15.789012Z"
  }
]
```

### Get Latest Metrics
```bash
TABLE="machine_kangroocare_pc1_benglore"

curl -s -H "X-Api-Key: 6aec8f303a91bedf21f9362257f9f4d5cb5168b1" \
  "http://164.52.221.241:8000/machines/${TABLE}/latest" | python3 -m json.tool
```

### Get Historical Metrics
```bash
TABLE="machine_kangroocare_pc1_benglore"

# Last 60 minutes
curl -s -H "X-Api-Key: 6aec8f303a91bedf21f9362257f9f4d5cb5168b1" \
  "http://164.52.221.241:8000/machines/${TABLE}/history?minutes=60" | python3 -m json.tool

# Last 24 hours
curl -s -H "X-Api-Key: 6aec8f303a91bedf21f9362257f9f4d5cb5168b1" \
  "http://164.52.221.241:8000/machines/${TABLE}/history?minutes=1440" | python3 -m json.tool
```

### Change API Secret Key
```bash
# Generate new key
NEW_KEY=$(openssl rand -hex 20)
echo "New key: $NEW_KEY"

# Update .env
sed -i "s/API_SECRET=.*/API_SECRET=$NEW_KEY/" /opt/reformmed-monitor/server/.env

# Restart API
docker restart reformmed_api

echo "⚠️  Update ALL agent .env files with new key: $NEW_KEY"
```

---

## 📈 Monitoring & Logs

### Complete System Status Check
```bash
echo "=== REFORMMED Monitor Status ==="
echo ""
echo "--- Containers ---"
docker ps --format "table {{.Names}}\t{{.Status}}"
echo ""
echo "--- API Health ---"
curl -s http://localhost:8000/health
echo ""
echo "--- Machines ---"
docker exec reformmed_postgres psql -U reformmed -d monitor_machine \
  -c "SELECT system_name, location, status, public_ip, EXTRACT(EPOCH FROM NOW()-last_seen)::int AS seconds_ago FROM machine_registry;" 2>/dev/null
echo ""
echo "--- DB Tables ---"
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "\dt" 2>/dev/null
echo ""
echo "--- Grafana Datasource ---"
curl -s -u 'admin:monitor2345' \
  -X POST http://localhost:3000/api/datasources/uid/PCC52D03280B7034C/health 2>/dev/null
echo ""
echo "--- Disk Usage on VM ---"
df -h | grep -v tmpfs | grep -v loop
```

### Container Logs
```bash
# API Server (metric collection)
docker logs reformmed_api --tail 50
docker logs reformmed_api -f

# Alert Checker (email alerts)
docker logs reformmed_checker --tail 50
docker logs reformmed_checker -f

# Dashboard Manager (auto-create dashboards)
docker logs reformmed_dashboard_manager --tail 50
docker logs reformmed_dashboard_manager -f

# Grafana
docker logs reformmed_grafana --tail 50

# PostgreSQL
docker logs reformmed_postgres --tail 50
```

### Check Container Resource Usage
```bash
docker stats --no-stream
```

### Check VM Disk Usage
```bash
df -h | grep -v tmpfs | grep -v loop
```

### Check VM Memory
```bash
free -h
```

### Check Network Ports
```bash
ss -tlnp | grep -E "8000|3000|5432"
```

### Monitor Real-Time Metrics (watch command)
```bash
# Watch machine status (refreshes every 2 seconds)
watch -n 2 'docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "SELECT system_name, status, EXTRACT(EPOCH FROM NOW()-last_seen)::int AS sec_ago FROM machine_registry;"'

# Watch latest CPU/RAM for a machine
TABLE="machine_kangroocare_pc1_benglore"
watch -n 2 "docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c 'SELECT ts, cpu_percent, ram_percent FROM ${TABLE} ORDER BY ts DESC LIMIT 1;'"
```

---

## 🔧 Troubleshooting

### Issue: Containers Not Starting
```bash
# Check logs
cd /opt/reformmed-monitor/server
docker compose --env-file .env logs

# Rebuild
docker compose --env-file .env up -d --build
```

### Issue: Grafana Shows "No Data"
```bash
# Check datasource
curl -s -u 'admin:monitor2345' \
  -X POST http://localhost:3000/api/datasources/uid/PCC52D03280B7034C/health

# Restart dashboard manager
docker restart reformmed_dashboard_manager
```

### Issue: Dashboard Manager Shows 401 Errors
```bash
# Check Grafana password matches
grep GRAFANA_PASS /opt/reformmed-monitor/server/.env

# Check dashboard_manager.py credentials
grep "b64encode" /opt/reformmed-monitor/server/dashboard_manager.py

# Reset Grafana password to default
docker exec reformmed_grafana grafana-cli admin reset-admin-password monitor2345

# Restart dashboard manager
docker restart reformmed_dashboard_manager
```

### Issue: Agent Not Connecting
```bash
# On client machine — check agent logs
# Linux:
journalctl -u reformmed-agent --no-pager -n 20

# Windows:
Get-ScheduledTask -TaskName 'ReformmedMonitorAgent' | Select State

# Check server reachable from client
curl http://164.52.221.241:8000/health

# Check firewall on server
ufw status
ufw allow 8000/tcp
ufw allow 3000/tcp
```

### Issue: Email Alerts Not Sending
```bash
# Check checker logs
docker logs reformmed_checker --tail 30

# Verify Gmail settings
grep -E "GMAIL|ALERT_TO" /opt/reformmed-monitor/server/.env

# Test email manually (see Alert section above)
```

### Issue: Spam Disk Alerts (snap/loop devices)
```bash
# Update agent to latest version (already filters snap/loop)
# On client machine:
sudo curl -sSL https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/agent.py \
  -o /opt/reformmed-agent/agent.py
sudo systemctl restart reformmed-agent
```

### Issue: Ports Not Accessible
```bash
# Check firewall
ufw status
ufw allow 8000/tcp
ufw allow 3000/tcp

# Check ports are bound
ss -tlnp | grep -E "8000|3000"

# Check if services are listening
netstat -tulpn | grep -E "8000|3000"
```

### Issue: Database Connection Errors
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs reformmed_postgres --tail 50

# Restart PostgreSQL
docker restart reformmed_postgres
sleep 10
docker restart reformmed_api reformmed_checker reformmed_dashboard_manager
```

### Issue: Agent Registers as "unknown"
```bash
# On client machine — fix .env
# Linux:
sudo nano /opt/reformmed-agent/.env
# Set REFORMMED_SYSTEM_NAME=Your-Machine-Name (no spaces, use dashes)
sudo systemctl restart reformmed-agent

# Windows:
notepad C:\reformmed-agent\.env
# Set REFORMMED_SYSTEM_NAME=Your-Machine-Name (no spaces, use dashes)
Stop-ScheduledTask -TaskName 'ReformmedMonitorAgent'
Start-ScheduledTask -TaskName 'ReformmedMonitorAgent'
```

---

## 💾 Backup & Recovery

### Full System Backup
```bash
# Create backup directory
mkdir -p /opt/backups/reformmed-monitor

# Backup database
docker exec reformmed_postgres pg_dump -U reformmed monitor_machine | \
  gzip > /opt/backups/reformmed-monitor/db_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup .env and config files
tar -czf /opt/backups/reformmed-monitor/config_$(date +%Y%m%d_%H%M%S).tar.gz \
  /opt/reformmed-monitor/server/.env \
  /opt/reformmed-monitor/server/docker-compose.yml \
  /opt/reformmed-monitor/server/main.py \
  /opt/reformmed-monitor/server/offline_checker.py \
  /opt/reformmed-monitor/server/dashboard_manager.py

echo "✅ Backup complete"
ls -lh /opt/backups/reformmed-monitor/
```

### Automated Daily Backup (Cron)
```bash
# Create backup script
cat > /opt/backups/backup-reformmed.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/opt/backups/reformmed-monitor
mkdir -p $BACKUP_DIR

# Database backup
docker exec reformmed_postgres pg_dump -U reformmed monitor_machine | \
  gzip > $BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "$(date): Backup complete" >> $BACKUP_DIR/backup.log
EOF

chmod +x /opt/backups/backup-reformmed.sh

# Add to crontab (runs daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/backups/backup-reformmed.sh") | crontab -
```

### Restore from Backup
```bash
# Stop services
cd /opt/reformmed-monitor/server
docker compose --env-file .env down

# Restore database
gunzip < /opt/backups/reformmed-monitor/db_20260218_120000.sql.gz | \
  docker exec -i reformmed_postgres psql -U reformmed -d monitor_machine

# Start services
docker compose --env-file .env up -d

echo "✅ Restore complete"
```

### Disaster Recovery (Complete Rebuild)
```bash
# On new VM:
# 1. Install Docker
apt update && apt install -y docker.io docker-compose

# 2. Clone repo
cd /opt
git clone https://github.com/vivekdummi/com.server.reformmed.monitor.git reformmed-monitor

# 3. Restore .env
cp /backup/location/.env /opt/reformmed-monitor/server/.env

# 4. Start services
cd /opt/reformmed-monitor/server
docker compose --env-file .env up -d

# 5. Restore database
gunzip < /backup/location/db_backup.sql.gz | \
  docker exec -i reformmed_postgres psql -U reformmed -d monitor_machine

# 6. Verify
docker ps
curl http://localhost:8000/health
```

---

## 🔒 Security

### Change All Passwords
```bash
# 1. Grafana Password
docker exec reformmed_grafana grafana-cli admin reset-admin-password NEW_GRAFANA_PASS
sed -i 's/GRAFANA_PASS=.*/GRAFANA_PASS=NEW_GRAFANA_PASS/' /opt/reformmed-monitor/server/.env
sed -i 's/admin:monitor2345/admin:NEW_GRAFANA_PASS/g' /opt/reformmed-monitor/server/dashboard_manager.py
docker compose --env-file .env up -d --build dashboard_manager

# 2. PostgreSQL Password
# (Requires database recreation — backup first!)

# 3. API Secret Key
NEW_API_KEY=$(openssl rand -hex 20)
sed -i "s/API_SECRET=.*/API_SECRET=$NEW_API_KEY/" /opt/reformmed-monitor/server/.env
docker restart reformmed_api
echo "⚠️  Update all agent .env files with: $NEW_API_KEY"

# 4. Gmail App Password
# Generate new app password in Google Account settings
sed -i 's/GMAIL_APP_PASS=.*/GMAIL_APP_PASS=NEW_APP_PASS/' /opt/reformmed-monitor/server/.env
docker restart reformmed_checker
```

### Firewall Configuration
```bash
# Enable UFW
ufw enable

# Allow SSH
ufw allow 22/tcp

# Allow monitoring ports
ufw allow 8000/tcp comment 'REFORMMED API'
ufw allow 3000/tcp comment 'Grafana'

# Block PostgreSQL from external access
ufw deny 5432/tcp

# Check status
ufw status numbered
```

### SSL/TLS (HTTPS)
```bash
# Install Nginx as reverse proxy
apt install -y nginx certbot python3-certbot-nginx

# Configure Nginx for Grafana
cat > /etc/nginx/sites-available/reformmed-grafana << 'EOF'
server {
    listen 80;
    server_name monitor.reformmed.ai;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -s /etc/nginx/sites-available/reformmed-grafana /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# Get SSL certificate
certbot --nginx -d monitor.reformmed.ai

# Now access via https://monitor.reformmed.ai
```

### Restrict API Access by IP
```bash
# In main.py, add IP whitelist
nano /opt/reformmed-monitor/server/main.py

# Add before route definitions:
# ALLOWED_IPS = ["106.51.66.127", "164.52.221.241"]
# @app.middleware("http")
# async def check_ip(request, call_next):
#     client_ip = request.client.host
#     if client_ip not in ALLOWED_IPS:
#         return JSONResponse({"error": "Forbidden"}, status_code=403)
#     return await call_next(request)

# Rebuild
docker compose --env-file .env up -d --build api
```

---

## ⚡ Performance Tuning

### PostgreSQL Tuning
```bash
# Edit PostgreSQL config
docker exec -it reformmed_postgres bash
nano /var/lib/postgresql/data/postgresql.conf

# Add/update:
# shared_buffers = 256MB
# effective_cache_size = 1GB
# maintenance_work_mem = 128MB
# checkpoint_completion_target = 0.9
# wal_buffers = 16MB
# default_statistics_target = 100
# random_page_cost = 1.1
# work_mem = 4MB
# min_wal_size = 1GB
# max_wal_size = 4GB

# Restart PostgreSQL
docker restart reformmed_postgres
```

### Data Retention Policy (Auto-cleanup)
```bash
# Create cleanup script
cat > /opt/reformmed-monitor/cleanup-old-data.sh << 'EOF'
#!/bin/bash
# Delete data older than 30 days from all machine tables

docker exec reformmed_postgres psql -U reformmed -d monitor_machine << 'SQL'
DO $$
DECLARE
    tbl TEXT;
    deleted_count INTEGER;
BEGIN
    FOR tbl IN
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name LIKE 'machine_%' AND table_name != 'machine_registry'
    LOOP
        EXECUTE format('DELETE FROM %I WHERE ts < NOW() - INTERVAL ''30 days''', tbl);
        GET DIAGNOSTICS deleted_count = ROW_COUNT;
        RAISE NOTICE '% rows deleted from %', deleted_count, tbl;
    END LOOP;
END;
$$;
VACUUM ANALYZE;
SQL

echo "$(date): Cleanup complete" >> /opt/reformmed-monitor/cleanup.log
EOF

chmod +x /opt/reformmed-monitor/cleanup-old-data.sh

# Run weekly (Sundays at 3 AM)
(crontab -l 2>/dev/null; echo "0 3 * * 0 /opt/reformmed-monitor/cleanup-old-data.sh") | crontab -
```

### Optimize Docker
```bash
# Prune unused images
docker image prune -a -f

# Prune unused volumes
docker volume prune -f

# Limit container logs
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF

systemctl restart docker
```

---

## 🔄 Upgrade & Maintenance

### Update Server Code
```bash
cd /opt/reformmed-monitor
git pull origin main
cd server
docker compose --env-file .env up -d --build
```

### Update Agent on All Machines
```bash
# Linux (run on each client):
sudo curl -sSL https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/agent.py \
  -o /opt/reformmed-agent/agent.py
sudo systemctl restart reformmed-agent

# Windows (run on each client in PowerShell as Admin):
Stop-ScheduledTask -TaskName 'ReformmedMonitorAgent'
Invoke-WebRequest "https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/agent.py" `
    -OutFile "C:\reformmed-agent\agent.py" -UseBasicParsing
Start-ScheduledTask -TaskName 'ReformmedMonitorAgent'
```

### Upgrade Docker Compose
```bash
# Check current version
docker compose version

# Upgrade
apt update
apt install -y docker-compose-plugin

# Verify
docker compose version
```

### Upgrade PostgreSQL
```bash
# Backup first!
docker exec reformmed_postgres pg_dump -U reformmed monitor_machine | \
  gzip > /opt/backups/before_upgrade_$(date +%Y%m%d).sql.gz

# Update docker-compose.yml
nano /opt/reformmed-monitor/server/docker-compose.yml
# Change: image: postgres:16-alpine → image: postgres:17-alpine

# Restart
cd /opt/reformmed-monitor/server
docker compose --env-file .env down
docker compose --env-file .env up -d
```

### Maintenance Window Checklist
```bash
# 1. Announce maintenance
echo "Send notification to users"

# 2. Backup everything
/opt/backups/backup-reformmed.sh

# 3. Stop services
cd /opt/reformmed-monitor/server
docker compose --env-file .env down

# 4. Perform updates
git pull origin main
docker compose --env-file .env build

# 5. Start services
docker compose --env-file .env up -d

# 6. Verify all running
docker ps
curl http://localhost:8000/health
curl -u 'admin:monitor2345' http://localhost:3000/api/health

# 7. Check dashboards loading
# Open http://164.52.221.241:3000

# 8. Monitor logs for errors
docker logs reformmed_api --tail 50
docker logs reformmed_checker --tail 50
docker logs reformmed_dashboard_manager --tail 50
```

---

## 📚 Complete Command Reference

### Quick Commands
```bash
# Start everything
cd /opt/reformmed-monitor/server && docker compose --env-file .env up -d

# Stop everything
cd /opt/reformmed-monitor/server && docker compose --env-file .env down

# Restart everything
cd /opt/reformmed-monitor/server && docker compose --env-file .env restart

# View all logs
cd /opt/reformmed-monitor/server && docker compose --env-file .env logs -f

# Check status
docker ps && curl http://localhost:8000/health

# List machines
curl -s -H "X-Api-Key: 6aec8f303a91bedf21f9362257f9f4d5cb5168b1" http://localhost:8000/machines | python3 -m json.tool

# Force recreate dashboards
docker restart reformmed_dashboard_manager

# Backup database
docker exec reformmed_postgres pg_dump -U reformmed monitor_machine | gzip > backup_$(date +%Y%m%d).sql.gz

# Clean old data (30 days)
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "DELETE FROM machine_kangroocare_pc1_benglore WHERE ts < NOW() - INTERVAL '30 days';"
```

---

## 📝 Change Log

### Version 1.0 (February 18, 2026)
**Initial Production Release**

**Server Components:**
- ✅ FastAPI server for metric collection
- ✅ PostgreSQL database with per-machine tables
- ✅ Grafana with auto-provisioned datasource
- ✅ Email alert system (offline + threshold)
- ✅ Auto-dashboard manager
- ✅ Docker Compose orchestration

**Agent Features:**
- ✅ Ubuntu/Linux systemd service
- ✅ Windows Task Scheduler service
- ✅ One-liner installers
- ✅ Full GPU support (NVIDIA + Intel iGPU + AMD)
- ✅ Snap/loop device filtering
- ✅ Auto-restart on boot

**Key Changes:**
- Fixed Windows installer pip errors (use `python.exe -m pip`)
- Fixed snap/loop disk spam (filter at collection + alert)
- Fixed offline checker IST timezone
- Fixed dashboard manager registry creation
- Fixed Grafana 401 errors (credential sync)
- Added complete documentation

**Known Issues:**
- None

**Next Version Planned:**
- Web UI for agent management
- Role-based access control
- Slack/Teams integration
- Custom metric plugins

---

## 🔗 Links

| Resource | URL |
|---|---|
| **Server Repo** | https://github.com/vivekdummi/com.server.reformmed.monitor |
| **Agent Repo** | https://github.com/vivekdummi/com.agent.reformmed.monitor |
| **Grafana** | http://164.52.221.241:3000 |
| **API** | http://164.52.221.241:8000 |
| **Fleet Dashboard** | http://164.52.221.241:3000/d/reformmed-fleet |

---

## 📞 Support

For issues, questions, or feature requests:
- Email: info@reformmed.ai
- Documentation: This file + README.md in GitHub repos

---

*REFORMMED Monitor — Healthcare Infrastructure Monitoring*  
*Version 1.0 | Last Updated: February 18, 2026*
