#!/bin/bash
set -e

clear

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                           ║"
echo "║          🏥 REFORMMED Monitor — Fresh Installation Wizard                ║"
echo "║                                                                           ║"
echo "╚═══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "This will perform a FRESH installation. All existing data will be removed."
echo ""

# Check if existing installation
if [ -f "server/.env" ]; then
    echo "⚠️  WARNING: Existing installation detected!"
    echo ""
    read -p "Type 'YES' to continue with fresh install: " confirm
    if [[ "$confirm" != "YES" ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    echo ""
    echo "🗑️  Removing old installation..."
    cd server
    docker compose down -v 2>/dev/null || true
    cd ..
    rm -rf server/.env server/postgres_data server/grafana_data
    echo "✅ Old installation removed"
    echo ""
fi

# Function to generate secure password
generate_password() {
    openssl rand -base64 16 | tr -d "=+/" | cut -c1-16
}

# Function to generate API key
generate_api_key() {
    openssl rand -hex 32
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📋 STEP 1: SERVER CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Auto-detect IP
DETECTED_IP=$(curl -s ifconfig.me 2>/dev/null || echo "")
if [ -n "$DETECTED_IP" ]; then
    echo "🌐 Detected Public IP: $DETECTED_IP"
    read -p "Enter hostname or IP [$DETECTED_IP]: " SERVER_HOST
    SERVER_HOST=${SERVER_HOST:-$DETECTED_IP}
else
    read -p "Enter hostname or IP: " SERVER_HOST
    while [ -z "$SERVER_HOST" ]; do
        echo "❌ Server hostname/IP is required!"
        read -p "Enter hostname or IP: " SERVER_HOST
    done
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🗄️  STEP 2: POSTGRESQL DATABASE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "PostgreSQL Username [reformmed]: " POSTGRES_USER
POSTGRES_USER=${POSTGRES_USER:-reformmed}

read -sp "PostgreSQL Password [auto-generate]: " POSTGRES_PASSWORD
echo ""
if [ -z "$POSTGRES_PASSWORD" ]; then
    POSTGRES_PASSWORD=$(generate_password)
    echo "✅ Auto-generated secure password"
fi

POSTGRES_DB="monitor_machine"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📊 STEP 3: GRAFANA DASHBOARD"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Grafana Username [admin]: " GRAFANA_USER
GRAFANA_USER=${GRAFANA_USER:-admin}

read -sp "Grafana Password [auto-generate]: " GRAFANA_PASSWORD
echo ""
if [ -z "$GRAFANA_PASSWORD" ]; then
    GRAFANA_PASSWORD=$(generate_password)
    echo "✅ Auto-generated secure password"
fi

read -p "Dashboard refresh interval in seconds [5]: " GRAFANA_REFRESH
GRAFANA_REFRESH=${GRAFANA_REFRESH:-5}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📧 STEP 4: EMAIL ALERTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Gmail account for sending alerts: " GMAIL_USER
while [ -z "$GMAIL_USER" ]; do
    echo "❌ Gmail account is required!"
    read -p "Gmail account: " GMAIL_USER
done

echo ""
echo "ℹ️  Gmail App Password (can have spaces, will be cleaned automatically)"
read -p "Gmail App Password: " GMAIL_APP_PASS
GMAIL_APP_PASS=$(echo "$GMAIL_APP_PASS" | tr -d ' ')
while [ -z "$GMAIL_APP_PASS" ]; do
    echo "❌ Gmail App Password is required!"
    read -p "Gmail App Password: " GMAIL_APP_PASS
    GMAIL_APP_PASS=$(echo "$GMAIL_APP_PASS" | tr -d ' ')
done

echo ""
echo "📨 Alert Recipients (separate multiple emails with comma)"
echo "Example: admin@company.com, ops@company.com"
read -p "Alert emails: " ALERT_EMAILS
while [ -z "$ALERT_EMAILS" ]; do
    echo "❌ At least one email is required!"
    read -p "Alert emails: " ALERT_EMAILS
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ⚙️  STEP 5: ALERT THRESHOLDS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🔺 HIGH Usage Alerts (send alert when ABOVE these values):"
read -p "  CPU threshold % [90]: " CPU_THRESHOLD
CPU_THRESHOLD=${CPU_THRESHOLD:-90}

read -p "  RAM threshold % [90]: " RAM_THRESHOLD
RAM_THRESHOLD=${RAM_THRESHOLD:-90}

read -p "  Disk threshold % [85]: " DISK_THRESHOLD
DISK_THRESHOLD=${DISK_THRESHOLD:-85}

read -p "  Temperature threshold °C [80]: " TEMP_THRESHOLD
TEMP_THRESHOLD=${TEMP_THRESHOLD:-80}

echo ""
echo "🔻 LOW Resource Alerts (send alert when BELOW these values):"
read -p "  RAM free % [10]: " RAM_LOW_THRESHOLD
RAM_LOW_THRESHOLD=${RAM_LOW_THRESHOLD:-10}

read -p "  Disk free % [10]: " DISK_LOW_THRESHOLD
DISK_LOW_THRESHOLD=${DISK_LOW_THRESHOLD:-10}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ⏱️  STEP 6: MONITORING INTERVALS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "⏰ Offline/Online Detection:"
read -p "  Mark machine offline after seconds [10]: " OFFLINE_SECS
OFFLINE_SECS=${OFFLINE_SECS:-10}

read -p "  Check interval seconds [3]: " CHECK_INTERVAL
CHECK_INTERVAL=${CHECK_INTERVAL:-3}

read -p "  Alert cooldown minutes (no repeat alerts) [10]: " COOLDOWN_MINS
COOLDOWN_MINS=${COOLDOWN_MINS:-10}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔐 STEP 7: API SECURITY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

API_SECRET_KEY=$(generate_api_key)
echo "✅ API Secret Key auto-generated (64 characters)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ CONFIGURATION SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Server:          $SERVER_HOST"
echo "PostgreSQL:      $POSTGRES_USER / ********"
echo "Grafana:         $GRAFANA_USER / ********"
echo "Grafana Refresh: ${GRAFANA_REFRESH}s"
echo "Gmail:           $GMAIL_USER"
echo "Alert To:        $ALERT_EMAILS"
echo "CPU Alert:       > ${CPU_THRESHOLD}%"
echo "RAM Alert:       > ${RAM_THRESHOLD}% or < ${RAM_LOW_THRESHOLD}% free"
echo "Disk Alert:      > ${DISK_THRESHOLD}% or < ${DISK_LOW_THRESHOLD}% free"
echo "Temp Alert:      > ${TEMP_THRESHOLD}°C"
echo "Offline After:   ${OFFLINE_SECS}s"
echo "Check Interval:  ${CHECK_INTERVAL}s"
echo ""
read -p "Proceed with installation? [Y/n]: " PROCEED
if [[ "$PROCEED" == "n" || "$PROCEED" == "N" ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 INSTALLING..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Create .env file
echo "📝 Creating configuration..."

cat > server/.env << ENV_EOF
# Database
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
POSTGRES_HOST=reformmed_postgres
POSTGRES_PORT=5432

# API
API_SECRET=${API_SECRET_KEY}
API_HOST=0.0.0.0
API_PORT=8000

# Grafana
GRAFANA_USER=${GRAFANA_USER}
GRAFANA_PASS=${GRAFANA_PASSWORD}
GRAFANA_URL=http://reformmed_grafana:3000
GRAFANA_REFRESH=${GRAFANA_REFRESH}s

# Email
GMAIL_USER=${GMAIL_USER}
GMAIL_APP_PASS=${GMAIL_APP_PASS}
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
ALERT_TO=${ALERT_EMAILS}

# Thresholds
CPU_ALERT_THRESH=${CPU_THRESHOLD}
RAM_ALERT_THRESH=${RAM_THRESHOLD}
DISK_ALERT_THRESH=${DISK_THRESHOLD}
TEMP_ALERT_THRESH=${TEMP_THRESHOLD}
RAM_LOW_THRESH=${RAM_LOW_THRESHOLD}
DISK_LOW_THRESH=${DISK_LOW_THRESHOLD}

# Monitoring
OFFLINE_AFTER_SECS=${OFFLINE_SECS}
CHECK_INTERVAL_SECS=${CHECK_INTERVAL}
ALERT_COOLDOWN_MINUTES=${COOLDOWN_MINS}
ENV_EOF

echo "✅ Configuration saved"
echo ""

# Check Docker
echo "🐳 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found! Please install Docker first."
    exit 1
fi
echo "✅ Docker found"
echo ""

# Start containers
echo "🚀 Starting Docker containers..."
cd server
docker compose --env-file .env up -d --build

echo ""
echo "⏳ Waiting for services to start..."
for i in {1..30}; do
    echo -n "."
    sleep 1
done
echo ""
echo ""

# Initialize database
echo "📊 Initializing database..."

docker exec -i reformmed_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} << 'SQL'
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key TEXT UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS email_recipients (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    receive_all_alerts BOOLEAN DEFAULT true,
    locations TEXT[],
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS machine_alert_settings (
    id SERIAL PRIMARY KEY,
    table_name TEXT UNIQUE NOT NULL,
    alerts_enabled BOOLEAN DEFAULT true,
    cpu_threshold INT,
    ram_threshold INT,
    disk_threshold INT,
    temp_threshold INT,
    ram_low_threshold INT,
    disk_low_threshold INT,
    send_offline_alerts BOOLEAN DEFAULT true,
    send_threshold_alerts BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

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

# Insert config
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
    ('grafana_user', '${GRAFANA_USER}', 'Grafana username'),
    ('grafana_password', '${GRAFANA_PASSWORD}', 'Grafana password'),
    ('grafana_refresh', '${GRAFANA_REFRESH}s', 'Dashboard refresh interval'),
    ('gmail_user', '${GMAIL_USER}', 'Gmail account'),
    ('gmail_app_password', '${GMAIL_APP_PASS}', 'Gmail app password'),
    ('smtp_host', 'smtp.gmail.com', 'SMTP server'),
    ('smtp_port', '465', 'SMTP port'),
    ('offline_after_secs', '${OFFLINE_SECS}', 'Mark offline after N seconds'),
    ('check_interval_secs', '${CHECK_INTERVAL}', 'Alert check interval'),
    ('default_cpu_threshold', '${CPU_THRESHOLD}', 'Default CPU threshold %'),
    ('default_ram_threshold', '${RAM_THRESHOLD}', 'Default RAM threshold %'),
    ('default_disk_threshold', '${DISK_THRESHOLD}', 'Default Disk threshold %'),
    ('default_temp_threshold', '${TEMP_THRESHOLD}', 'Default Temp threshold °C'),
    ('default_ram_low_threshold', '${RAM_LOW_THRESHOLD}', 'Default RAM low threshold %'),
    ('default_disk_low_threshold', '${DISK_LOW_THRESHOLD}', 'Default Disk low threshold %'),
    ('alert_cooldown_minutes', '${COOLDOWN_MINS}', 'Alert cooldown minutes')
ON CONFLICT (config_key) DO UPDATE SET config_value=EXCLUDED.config_value;
SQL

# Insert email recipients
IFS=',' read -ra EMAILS <<< "$ALERT_EMAILS"
for email in "${EMAILS[@]}"; do
    email=$(echo "$email" | xargs)
    docker exec reformmed_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} << SQL
INSERT INTO email_recipients (email, name, receive_all_alerts) 
VALUES ('${email}', '${email}', true)
ON CONFLICT (email) DO NOTHING;
SQL
done

echo "✅ Database initialized"
echo ""

# Test services
echo "🔍 Testing services..."
sleep 5

API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
GRAFANA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" http://localhost:3000/api/health)

if [[ "$API_STATUS" == "200" ]]; then
    echo "✅ API is healthy"
else
    echo "⚠️  API status: $API_STATUS"
fi

if [[ "$GRAFANA_STATUS" == "200" ]]; then
    echo "✅ Grafana is healthy"
else
    echo "⚠️  Grafana status: $GRAFANA_STATUS"
fi

echo ""
echo "🐳 Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep reformmed

cd ..

# Save credentials
CREDS_FILE="CREDENTIALS_$(date +%Y%m%d_%H%M%S).txt"

cat > ${CREDS_FILE} << CREDS_EOF
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║         🎉 REFORMMED Monitor — Installation Complete! 🎉                 ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝

📅 Date: $(date '+%d %B %Y %H:%M:%S %Z')
🌍 Server: ${SERVER_HOST}

═══════════════════════════════════════════════════════════════════════════
  🌐 WEB ACCESS
═══════════════════════════════════════════════════════════════════════════

📊 Grafana Dashboard:
  URL:      http://${SERVER_HOST}:3000
  Username: ${GRAFANA_USER}
  Password: ${GRAFANA_PASSWORD}
  Refresh:  ${GRAFANA_REFRESH}s

🔌 API Endpoint:
  URL:      http://${SERVER_HOST}:8000
  Health:   http://${SERVER_HOST}:8000/health
  Status:   ${API_STATUS}

═══════════════════════════════════════════════════════════════════════════
  🗄️  DATABASE
═══════════════════════════════════════════════════════════════════════════

PostgreSQL Connection:
  Host:     ${SERVER_HOST}:5432
  Database: ${POSTGRES_DB}
  Username: ${POSTGRES_USER}
  Password: ${POSTGRES_PASSWORD}

Connect Command:
  docker exec -it reformmed_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

═══════════════════════════════════════════════════════════════════════════
  🔑 API KEY (for agents)
═══════════════════════════════════════════════════════════════════════════

API Secret Key:
  ${API_SECRET_KEY}

⚠️  Keep this secret! Use it when installing agents.

═══════════════════════════════════════════════════════════════════════════
  📧 EMAIL ALERTS
═══════════════════════════════════════════════════════════════════════════

Gmail Account:     ${GMAIL_USER}
App Password:      ${GMAIL_APP_PASS}
Recipients:        ${ALERT_EMAILS}

Alert Thresholds:
  🔺 HIGH Alerts (when usage exceeds):
    • CPU:         > ${CPU_THRESHOLD}%
    • RAM:         > ${RAM_THRESHOLD}%
    • Disk:        > ${DISK_THRESHOLD}%
    • Temperature: > ${TEMP_THRESHOLD}°C
  
  🔻 LOW Alerts (when free resources below):
    • RAM Free:    < ${RAM_LOW_THRESHOLD}%
    • Disk Free:   < ${DISK_LOW_THRESHOLD}%

Monitoring:
  • Offline after:  ${OFFLINE_SECS} seconds
  • Check interval: ${CHECK_INTERVAL} seconds
  • Cooldown:       ${COOLDOWN_MINS} minutes

═══════════════════════════════════════════════════════════════════════════
  🤖 INSTALL AGENTS ON CLIENT MACHINES
═══════════════════════════════════════════════════════════════════════════

Ubuntu/Linux (run as root):
  curl -sSL https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/install-linux.sh | sudo bash

Windows (PowerShell as Administrator):
  irm https://raw.githubusercontent.com/vivekdummi/com.agent.reformmed.monitor/main/install-windows.ps1 | iex

When prompted, enter:
  VM Server IP:  ${SERVER_HOST}
  Port:          8000
  API Secret:    ${API_SECRET_KEY}
  Machine Name:  [Your-Machine-Name]
  Location:      [Location-Name]
  Interval:      1

═══════════════════════════════════════════════════════════════════════════
  🐳 DOCKER COMMANDS
═══════════════════════════════════════════════════════════════════════════

Start:   cd /opt/reformmed-monitor/server && docker compose --env-file .env up -d
Stop:    cd /opt/reformmed-monitor/server && docker compose --env-file .env down
Restart: cd /opt/reformmed-monitor/server && docker compose --env-file .env restart
Logs:    docker logs reformmed_api --tail 50 -f

═══════════════════════════════════════════════════════════════════════════
  ⚠️  SECURITY
═══════════════════════════════════════════════════════════════════════════

1. 💾 SAVE THIS FILE IN A SECURE LOCATION
2. 🗑️  Delete from server after saving elsewhere
3. 🔥 Enable firewall:
     ufw allow 22/tcp
     ufw allow 8000/tcp
     ufw allow 3000/tcp
     ufw enable
4. 🔐 Change passwords after first login in Grafana
5. 🚫 Never share API key publicly

═══════════════════════════════════════════════════════════════════════════
  📚 DOCUMENTATION & SUPPORT
═══════════════════════════════════════════════════════════════════════════

GitHub:  https://github.com/vivekdummi/com.server.reformmed.monitor
Docs:    /COMPLETE_SERVER_GUIDE.md
Support: info@reformmed.ai

═══════════════════════════════════════════════════════════════════════════
CREDS_EOF

# Display credentials
clear
cat ${CREDS_FILE}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💾 Credentials saved to: ${CREDS_FILE}"
echo ""
echo "⚠️  IMPORTANT:"
echo "   1. Copy this file to a secure location"
echo "   2. Delete it from the server: rm ${CREDS_FILE}"
echo "   3. Start installing agents on client machines!"
echo ""
echo "🚀 Installation complete!"
echo ""

