#!/bin/bash
set -e

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║     🏥 REFORMMED Monitor — Server Installation           ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Generate random passwords and API keys
generate_password() {
    openssl rand -base64 16 | tr -d "=+/" | cut -c1-16
}

generate_api_key() {
    openssl rand -hex 32
}

# Check if this is first-time setup
if [ -f "server/.env" ]; then
    echo "⚠️  WARNING: server/.env already exists!"
    echo ""
    read -p "Do you want to OVERWRITE existing installation? [y/N]: " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    echo ""
    echo "🗑️  Removing old installation..."
    cd server
    docker compose down -v 2>/dev/null || true
    cd ..
    rm -rf server/.env
fi

echo "📋 Enter configuration details:"
echo ""

# Get user inputs
read -p "Server Public IP [$(curl -s ifconfig.me)]: " SERVER_IP
SERVER_IP=${SERVER_IP:-$(curl -s ifconfig.me)}

read -p "Gmail account for alerts [info@reformmed.ai]: " GMAIL_USER
GMAIL_USER=${GMAIL_USER:-info@reformmed.ai}

read -p "Gmail App Password: " GMAIL_APP_PASS
while [ -z "$GMAIL_APP_PASS" ]; do
    echo "❌ Gmail App Password is required!"
    read -p "Gmail App Password: " GMAIL_APP_PASS
done

read -p "Admin email (receives all alerts) [info@reformmed.ai]: " ADMIN_EMAIL
ADMIN_EMAIL=${ADMIN_EMAIL:-info@reformmed.ai}

read -p "Additional alert emails (comma-separated) [optional]: " ADDITIONAL_EMAILS

echo ""
echo "🔐 Generating secure credentials..."

# Generate credentials
POSTGRES_USER="reformmed"
POSTGRES_PASSWORD=$(generate_password)
POSTGRES_DB="monitor_machine"

GRAFANA_USER="admin"
GRAFANA_PASSWORD=$(generate_password)

API_SECRET_KEY=$(generate_api_key)

echo "✅ Credentials generated"
echo ""

# Create .env file
echo "📝 Creating configuration file..."

cat > server/.env << ENV_EOF
# Database Configuration
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_HOST=reformmed_postgres
POSTGRES_PORT=5432

# API Configuration
API_SECRET=${API_SECRET_KEY}
API_HOST=0.0.0.0
API_PORT=8000

# Grafana Configuration
GRAFANA_USER=${GRAFANA_USER}
GRAFANA_PASS=${GRAFANA_PASSWORD}
GRAFANA_URL=http://reformmed_grafana:3000

# Email Configuration
GMAIL_USER=${GMAIL_USER}
GMAIL_APP_PASS=${GMAIL_APP_PASS}
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465

# Alert Configuration
OFFLINE_AFTER_SECS=10
CHECK_INTERVAL_SECS=3
CPU_ALERT_THRESH=90
RAM_ALERT_THRESH=90
DISK_ALERT_THRESH=85
TEMP_ALERT_THRESH=80
ALERT_COOLDOWN_MINUTES=10

# Default alert recipients
ALERT_TO=${ADMIN_EMAIL}
ENV_EOF

echo "✅ Configuration file created"
echo ""

# Start Docker containers
echo "🐳 Starting Docker containers..."
cd server
docker compose --env-file .env up -d --build

echo ""
echo "⏳ Waiting for services to start (30 seconds)..."
sleep 30

# Check services
echo ""
echo "🔍 Checking services..."
docker ps --format "table {{.Names}}\t{{.Status}}" | grep reformmed

echo ""
echo "📊 Setting up database..."

# Initialize database with configuration tables
docker exec -i reformmed_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} << 'SQL'
-- System Configuration Table
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key TEXT UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email Recipients
CREATE TABLE IF NOT EXISTS email_recipients (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    receive_all_alerts BOOLEAN DEFAULT true,
    locations TEXT[],
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Machine Alert Settings
CREATE TABLE IF NOT EXISTS machine_alert_settings (
    id SERIAL PRIMARY KEY,
    table_name TEXT UNIQUE NOT NULL,
    alerts_enabled BOOLEAN DEFAULT true,
    cpu_threshold INT,
    ram_threshold INT,
    disk_threshold INT,
    temp_threshold INT,
    send_offline_alerts BOOLEAN DEFAULT true,
    send_threshold_alerts BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert History
CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    machine_table TEXT NOT NULL,
    machine_name TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    alert_value FLOAT,
    threshold FLOAT,
    recipients TEXT[],
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_history_lookup 
ON alert_history(machine_table, alert_type, sent_at DESC);

-- Machine Registry (if not exists)
CREATE TABLE IF NOT EXISTS machine_registry (
    id SERIAL PRIMARY KEY,
    system_name TEXT NOT NULL,
    location TEXT NOT NULL,
    table_name TEXT NOT NULL UNIQUE,
    os_type TEXT,
    hostname TEXT,
    public_ip TEXT,
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ,
    status TEXT DEFAULT 'offline'
);
SQL

# Insert config values
docker exec reformmed_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} << SQL
INSERT INTO system_config (config_key, config_value, description) VALUES
    ('db_host', 'reformmed_postgres', 'PostgreSQL hostname'),
    ('db_port', '5432', 'PostgreSQL port'),
    ('db_name', '${POSTGRES_DB}', 'Database name'),
    ('db_user', '${POSTGRES_USER}', 'Database username'),
    ('db_password', '${POSTGRES_PASSWORD}', 'Database password'),
    ('api_secret_key', '${API_SECRET_KEY}', 'API authentication key'),
    ('api_port', '8000', 'API bind port'),
    ('grafana_url', 'http://reformmed_grafana:3000', 'Grafana URL'),
    ('grafana_user', '${GRAFANA_USER}', 'Grafana admin username'),
    ('grafana_password', '${GRAFANA_PASSWORD}', 'Grafana admin password'),
    ('gmail_user', '${GMAIL_USER}', 'Gmail account'),
    ('gmail_app_password', '${GMAIL_APP_PASS}', 'Gmail app password'),
    ('smtp_host', 'smtp.gmail.com', 'SMTP server'),
    ('smtp_port', '465', 'SMTP port'),
    ('offline_after_secs', '10', 'Mark offline after N seconds'),
    ('check_interval_secs', '3', 'Alert check interval'),
    ('default_cpu_threshold', '90', 'Default CPU threshold %'),
    ('default_ram_threshold', '90', 'Default RAM threshold %'),
    ('default_disk_threshold', '85', 'Default Disk threshold %'),
    ('default_temp_threshold', '80', 'Default Temp threshold °C'),
    ('alert_cooldown_minutes', '10', 'Minutes between repeat alerts')
ON CONFLICT (config_key) DO NOTHING;

INSERT INTO email_recipients (email, name, receive_all_alerts) VALUES
    ('${ADMIN_EMAIL}', 'Admin', true)
ON CONFLICT (email) DO NOTHING;
SQL

# Add additional emails if provided
if [ -n "$ADDITIONAL_EMAILS" ]; then
    IFS=',' read -ra EMAILS <<< "$ADDITIONAL_EMAILS"
    for email in "${EMAILS[@]}"; do
        email=$(echo "$email" | xargs)  # Trim whitespace
        docker exec reformmed_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} << SQL
INSERT INTO email_recipients (email, name, receive_all_alerts) VALUES
    ('${email}', '${email}', true)
ON CONFLICT (email) DO NOTHING;
SQL
    done
fi

echo "✅ Database initialized"
echo ""

# Test API
echo "🔍 Testing API health..."
sleep 5
API_HEALTH=$(curl -s http://localhost:8000/health)
if [[ "$API_HEALTH" == *"ok"* ]]; then
    echo "✅ API is healthy"
else
    echo "⚠️  API may not be ready yet"
fi

echo ""
echo "🎉 Testing Grafana..."
GRAFANA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" http://localhost:3000/api/health)
if [[ "$GRAFANA_STATUS" == "200" ]]; then
    echo "✅ Grafana is accessible"
else
    echo "⚠️  Grafana may not be ready yet (status: ${GRAFANA_STATUS})"
fi

# Save credentials to file
CREDS_FILE="credentials_$(date +%Y%m%d_%H%M%S).txt"
cat > ${CREDS_FILE} << CREDS_EOF
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║              🏥 REFORMMED Monitor — Installation Complete                ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

📅 Installation Date: $(date '+%d %B %Y %H:%M:%S')
🌍 Server IP: ${SERVER_IP}

═══════════════════════════════════════════════════════════════════════════
  🌐 WEB ACCESS
═══════════════════════════════════════════════════════════════════════════

Grafana Dashboard:
  URL:      http://${SERVER_IP}:3000
  Username: ${GRAFANA_USER}
  Password: ${GRAFANA_PASSWORD}

API Endpoint:
  URL:      http://${SERVER_IP}:8000
  Health:   http://${SERVER_IP}:8000/health

═══════════════════════════════════════════════════════════════════════════
  🗄️  DATABASE ACCESS
═══════════════════════════════════════════════════════════════════════════

PostgreSQL:
  Host:     ${SERVER_IP}
  Port:     5432
  Database: ${POSTGRES_DB}
  Username: ${POSTGRES_USER}
  Password: ${POSTGRES_PASSWORD}

Connect:  psql -h ${SERVER_IP} -U ${POSTGRES_USER} -d ${POSTGRES_DB}

═══════════════════════════════════════════════════════════════════════════
  🔑 API AUTHENTICATION
═══════════════════════════════════════════════════════════════════════════

API Secret Key (for agents):
  ${API_SECRET_KEY}

Use this key when installing agents on client machines.

═══════════════════════════════════════════════════════════════════════════
  📧 EMAIL ALERTS
═══════════════════════════════════════════════════════════════════════════

Gmail Account:    ${GMAIL_USER}
App Password:     ${GMAIL_APP_PASS}
SMTP Server:      smtp.gmail.com:465

Alert Recipients:
  • ${ADMIN_EMAIL} (receives ALL alerts)
$(if [ -n "$ADDITIONAL_EMAILS" ]; then
    IFS=',' read -ra EMAILS <<< "$ADDITIONAL_EMAILS"
    for email in "${EMAILS[@]}"; do
        echo "  • $(echo $email | xargs)"
    done
fi)

═══════════════════════════════════════════════════════════════════════════
  🤖 AGENT INSTALLATION
═══════════════════════════════════════════════════════════════════════════

Ubuntu/Linux (run as root):
  curl -sSL https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/install-linux.sh | sudo bash

Windows (PowerShell as Administrator):
  irm https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/install-windows.ps1 | iex

Installation Inputs:
  VM Server IP:  ${SERVER_IP}
  Port:          8000
  API Secret:    ${API_SECRET_KEY}
  Machine Name:  [Your machine name]
  Location:      [Your location]
  Interval:      1

═══════════════════════════════════════════════════════════════════════════
  🐳 DOCKER MANAGEMENT
═══════════════════════════════════════════════════════════════════════════

Location: /opt/reformmed-monitor/server

Start all:    cd /opt/reformmed-monitor/server && docker compose --env-file .env up -d
Stop all:     cd /opt/reformmed-monitor/server && docker compose --env-file .env down
View logs:    docker logs reformmed_api --tail 50
Restart:      cd /opt/reformmed-monitor/server && docker compose --env-file .env restart

═══════════════════════════════════════════════════════════════════════════
  📊 MONITORING
═══════════════════════════════════════════════════════════════════════════

Fleet Overview:
  http://${SERVER_IP}:3000/d/reformmed-fleet

Individual machine dashboards will be auto-created when agents register.

═══════════════════════════════════════════════════════════════════════════
  ⚠️  SECURITY NOTES
═══════════════════════════════════════════════════════════════════════════

1. SAVE THIS FILE IN A SECURE LOCATION
2. Delete this file after saving credentials elsewhere
3. Enable firewall:
   ufw allow 22/tcp
   ufw allow 8000/tcp
   ufw allow 3000/tcp
   ufw enable

4. Change passwords after first login
5. Do NOT share API secret key publicly

═══════════════════════════════════════════════════════════════════════════
  📚 DOCUMENTATION
═══════════════════════════════════════════════════════════════════════════

Complete Guide:
  https://github.com/vivekdummi/com.server.reformmed.monitor/blob/main/COMPLETE_SERVER_GUIDE.md

Support: info@reformmed.ai

═══════════════════════════════════════════════════════════════════════════
CREDS_EOF

# Display credentials
cat ${CREDS_FILE}

echo ""
echo "💾 Credentials saved to: ${CREDS_FILE}"
echo ""
echo "⚠️  IMPORTANT: Save this file securely and delete it from the server after noting credentials!"
echo ""
echo "🚀 Installation complete! You can now install agents on client machines."
echo ""

cd ..
