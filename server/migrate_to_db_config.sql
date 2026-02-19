-- ============================================
-- REFORMMED Monitor - Database Configuration
-- Move all settings from .env to database
-- ============================================

-- 1. System Configuration (replaces .env)
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key TEXT UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default config from .env
INSERT INTO system_config (config_key, config_value, description) VALUES
    -- Database
    ('db_host', 'reformmed_postgres', 'PostgreSQL hostname'),
    ('db_port', '5432', 'PostgreSQL port'),
    ('db_name', 'monitor_machine', 'Database name'),
    ('db_user', 'reformmed', 'Database username'),
    ('db_password', 'monitor2345', 'Database password'),
    
    -- API
    ('api_secret_key', '6aec8f303a91bedf21f9362257f9f4d5cb5168b1', 'API authentication key'),
    ('api_host', '0.0.0.0', 'API bind host'),
    ('api_port', '8000', 'API bind port'),
    
    -- Grafana
    ('grafana_url', 'http://reformmed_grafana:3000', 'Grafana URL'),
    ('grafana_user', 'admin', 'Grafana admin username'),
    ('grafana_password', 'monitor2345', 'Grafana admin password'),
    
    -- Email
    ('gmail_user', 'info@reformmed.ai', 'Gmail account'),
    ('gmail_app_password', 'dhzlqwyppbywcfmj', 'Gmail app password'),
    ('smtp_host', 'smtp.gmail.com', 'SMTP server'),
    ('smtp_port', '465', 'SMTP port'),
    
    -- Global Alert Defaults
    ('offline_after_secs', '10', 'Mark machine offline after N seconds'),
    ('check_interval_secs', '3', 'Alert checker interval'),
    ('default_cpu_threshold', '90', 'Default CPU alert threshold %'),
    ('default_ram_threshold', '90', 'Default RAM alert threshold %'),
    ('default_disk_threshold', '85', 'Default Disk alert threshold %'),
    ('default_temp_threshold', '80', 'Default Temperature threshold °C'),
    ('alert_cooldown_minutes', '10', 'Minutes between repeat alerts')
ON CONFLICT (config_key) DO NOTHING;

-- 2. Email Recipients (replaces ALERT_TO)
CREATE TABLE IF NOT EXISTS email_recipients (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    role TEXT,
    receive_all_alerts BOOLEAN DEFAULT true,
    locations TEXT[], -- Array of locations this person monitors
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO email_recipients (email, name, role, receive_all_alerts, locations) VALUES
    ('info@reformmed.ai', 'REFORMMED Admin', 'admin', true, NULL),
    ('prakash@reformmed.ai', 'Prakash', 'manager', false, ARRAY['Salem', 'Bodycraft'])
ON CONFLICT (email) DO NOTHING;

-- 3. Per-Machine Alert Settings
CREATE TABLE IF NOT EXISTS machine_alert_settings (
    id SERIAL PRIMARY KEY,
    table_name TEXT UNIQUE NOT NULL REFERENCES machine_registry(table_name) ON DELETE CASCADE,
    
    -- Enable/disable alerts per machine
    alerts_enabled BOOLEAN DEFAULT true,
    
    -- Thresholds (NULL means use global default)
    cpu_threshold INT,
    ram_threshold INT,
    disk_threshold INT,
    temp_threshold INT,
    
    -- Email alert options
    send_offline_alerts BOOLEAN DEFAULT true,
    send_online_alerts BOOLEAN DEFAULT true,
    send_threshold_alerts BOOLEAN DEFAULT true,
    
    -- Custom recipient list (NULL means use default recipients)
    custom_recipients TEXT[],
    
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Alert History (track what alerts were sent)
CREATE TABLE IF NOT EXISTS alert_history (
    id SERIAL PRIMARY KEY,
    machine_table TEXT NOT NULL,
    machine_name TEXT NOT NULL,
    alert_type TEXT NOT NULL, -- 'offline', 'online', 'cpu', 'ram', 'disk', 'temp'
    alert_value FLOAT,
    threshold FLOAT,
    recipients TEXT[],
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for alert cooldown lookups
CREATE INDEX IF NOT EXISTS idx_alert_history_lookup 
ON alert_history(machine_table, alert_type, sent_at DESC);

-- 5. Dashboard Settings
CREATE TABLE IF NOT EXISTS dashboard_settings (
    id SERIAL PRIMARY KEY,
    table_name TEXT UNIQUE NOT NULL REFERENCES machine_registry(table_name) ON DELETE CASCADE,
    
    -- Grafana settings
    folder_name TEXT DEFAULT 'REFORMMED',
    refresh_interval TEXT DEFAULT '5s',
    time_range_from TEXT DEFAULT 'now-30m',
    time_range_to TEXT DEFAULT 'now',
    
    -- Panel visibility
    show_gpu_panels BOOLEAN DEFAULT true,
    show_network_panels BOOLEAN DEFAULT true,
    show_process_table BOOLEAN DEFAULT true,
    
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. API Keys (for agent authentication)
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_name TEXT UNIQUE NOT NULL,
    key_hash TEXT NOT NULL,
    key_plaintext TEXT, -- Store once for display, then null it out
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ
);

-- Add function to get config value
CREATE OR REPLACE FUNCTION get_config(key TEXT) 
RETURNS TEXT AS $$
    SELECT config_value FROM system_config WHERE config_key = key;
$$ LANGUAGE SQL STABLE;

-- Add function to update config value
CREATE OR REPLACE FUNCTION set_config(key TEXT, value TEXT) 
RETURNS VOID AS $$
    INSERT INTO system_config (config_key, config_value)
    VALUES (key, value)
    ON CONFLICT (config_key) 
    DO UPDATE SET config_value = value, updated_at = NOW();
$$ LANGUAGE SQL;

-- Add trigger to auto-create machine alert settings when machine registers
CREATE OR REPLACE FUNCTION create_machine_alert_settings()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO machine_alert_settings (table_name)
    VALUES (NEW.table_name)
    ON CONFLICT (table_name) DO NOTHING;
    
    INSERT INTO dashboard_settings (table_name)
    VALUES (NEW.table_name)
    ON CONFLICT (table_name) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_machine_settings
AFTER INSERT ON machine_registry
FOR EACH ROW
EXECUTE FUNCTION create_machine_alert_settings();

-- View for easy querying of machine alert config
CREATE OR REPLACE VIEW machine_alert_config AS
SELECT 
    mr.id,
    mr.system_name,
    mr.location,
    mr.table_name,
    mr.status,
    mas.alerts_enabled,
    COALESCE(mas.cpu_threshold, (SELECT config_value::int FROM system_config WHERE config_key='default_cpu_threshold')) as cpu_threshold,
    COALESCE(mas.ram_threshold, (SELECT config_value::int FROM system_config WHERE config_key='default_ram_threshold')) as ram_threshold,
    COALESCE(mas.disk_threshold, (SELECT config_value::int FROM system_config WHERE config_key='default_disk_threshold')) as disk_threshold,
    COALESCE(mas.temp_threshold, (SELECT config_value::int FROM system_config WHERE config_key='default_temp_threshold')) as temp_threshold,
    mas.send_offline_alerts,
    mas.send_online_alerts,
    mas.send_threshold_alerts,
    mas.custom_recipients
FROM machine_registry mr
LEFT JOIN machine_alert_settings mas ON mr.table_name = mas.table_name;

COMMENT ON TABLE system_config IS 'All system configuration (replaces .env file)';
COMMENT ON TABLE email_recipients IS 'Email recipients with location-based filtering';
COMMENT ON TABLE machine_alert_settings IS 'Per-machine alert thresholds and settings';
COMMENT ON TABLE alert_history IS 'Track all sent alerts for cooldown and audit';
COMMENT ON TABLE dashboard_settings IS 'Per-machine Grafana dashboard settings';
COMMENT ON TABLE api_keys IS 'API keys for agent authentication';
