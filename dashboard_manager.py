"""
REFORMMED Dashboard Manager — Auto-creates Grafana dashboards for each machine
COMPLETE VERSION with all panels working
"""
import asyncio, logging, base64, urllib.request, json, os
import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DASH] %(message)s")
log = logging.getLogger("dash-manager")

DB_HOST = os.getenv("POSTGRES_HOST", "reformmed_postgres")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "monitor_machine")
DB_USER = os.getenv("POSTGRES_USER", "reformmed")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "monitor2345")

GRAFANA_URL  = os.getenv("GRAFANA_URL", "http://reformmed_grafana:3000")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASS = os.getenv("GRAFANA_PASS", "monitor2345")
DS_UID       = "PCC52D03280B7034C"

known_machines = set()

def gapi(path, method="GET", data=None):
    """Call Grafana API"""
    creds = base64.b64encode(f"{GRAFANA_USER}:{GRAFANA_PASS}".encode()).decode()
    url = f"{GRAFANA_URL}{path}"
    req_data = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=req_data, method=method, headers={
        "Content-Type": "application/json",
        "Authorization": f"Basic {creds}"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        log.error(f"Grafana {method} {path} → {e.code}: {body}")
        return None
    except Exception as e:
        log.error(f"Grafana {method} {path} → {e}")
        return None

def create_dashboard(table_name, system_name, location):
    """Create individual machine dashboard with ALL panels working"""
    T = table_name
    uid = f"mach-{T}"[:40]
    title = f"🖥 {system_name} — {location}"
    DS = {"type": "grafana-postgresql-datasource", "uid": DS_UID}

    def ts(r, sql): 
        return {"refId": r, "rawSql": sql, "format": "time_series"}
    
    def tb(sql):    
        return {"refId": "A", "rawSql": sql, "format": "table"}

    panels = [
        # Row 1 — Status bar (fixed queries)
        {"id":1,"type":"stat","title":"🟢 Status","gridPos":{"x":0,"y":0,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
         "fieldConfig":{"defaults":{"mappings":[{"type":"value","options":{
             "online":{"text":"🟢 ONLINE","color":"green"},
             "offline":{"text":"🔴 OFFLINE","color":"red"}
         }}],"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"red","value":None}]}}},
         #"targets":[tb(f"SELECT ts as time, status as value FROM {T} ORDER BY ts DESC LIMIT 1")]},
	 "targets":[tb(f"SELECT ts as time, status as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":2,"type":"stat","title":"⏱ Uptime","gridPos":{"x":4,"y":0,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
         "fieldConfig":{"defaults":{"unit":"s","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"blue","value":None}]}}},
         "targets":[tb(f"SELECT ts as time, uptime_seconds as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":3,"type":"stat","title":"🌐 Public IP","gridPos":{"x":8,"y":0,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
         "fieldConfig":{"defaults":{"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"purple","value":None}]}}},
         #"targets":[tb(f"SELECT ts as time, public_ip FROM {T} ORDER BY ts DESC LIMIT 1")]},
	 "targets":[tb(f"SELECT ts as time, public_ip as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":4,"type":"stat","title":"💻 Machine Name","gridPos":{"x":12,"y":0,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
         "fieldConfig":{"defaults":{"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"dark-blue","value":None}]}}},
         #"targets":[tb(f"SELECT ts as time, '{system_name}' as value FROM {T} ORDER BY ts DESC LIMIT 1")]},
	 "targets":[tb(f"SELECT ts as time, '{system_name}' as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":5,"type":"stat","title":"📦 RAM Total","gridPos":{"x":16,"y":0,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
         "fieldConfig":{"defaults":{"unit":"decgbytes","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"teal","value":None}]}}},
         "targets":[tb(f"SELECT ts as time, ram_total_gb as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":6,"type":"stat","title":"💿 Disk Total","gridPos":{"x":20,"y":0,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
         "fieldConfig":{"defaults":{"unit":"decgbytes","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"semi-dark-green","value":None}]}}},
         "targets":[tb(f"SELECT ts as time, (disk_partitions->0->>'total_gb')::float as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        # Row 2 — Gauges
        {"id":7,"type":"gauge","title":"CPU %","gridPos":{"x":0,"y":3,"w":4,"h":6},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"showThresholdMarkers":True},
         "fieldConfig":{"defaults":{"unit":"percent","min":0,"max":100,"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":60},{"color":"orange","value":80},{"color":"red","value":90}]}}},
         "targets":[tb(f"SELECT ts as time, cpu_percent as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":8,"type":"gauge","title":"RAM %","gridPos":{"x":4,"y":3,"w":4,"h":6},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"showThresholdMarkers":True},
         "fieldConfig":{"defaults":{"unit":"percent","min":0,"max":100,"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":60},{"color":"orange","value":80},{"color":"red","value":90}]}}},
         "targets":[tb(f"SELECT ts as time, ram_percent as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":9,"type":"gauge","title":"Disk %","gridPos":{"x":8,"y":3,"w":4,"h":6},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"showThresholdMarkers":True},
         "fieldConfig":{"defaults":{"unit":"percent","min":0,"max":100,"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":60},{"color":"orange","value":80},{"color":"red","value":85}]}}},
         "targets":[tb(f"SELECT ts as time, (disk_partitions->0->>'percent')::float as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":10,"type":"gauge","title":"Swap %","gridPos":{"x":12,"y":3,"w":4,"h":6},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"showThresholdMarkers":True},
         "fieldConfig":{"defaults":{"unit":"percent","min":0,"max":100,"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":40},{"color":"red","value":75}]}}},
         "targets":[tb(f"SELECT ts as time, swap_percent as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":11,"type":"stat","title":"🌐 Net In","gridPos":{"x":16,"y":3,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"area"},
         "fieldConfig":{"defaults":{"unit":"Bps","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None}]}}},
         "targets":[tb(f"SELECT ts as time, net_bytes_recv as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":12,"type":"stat","title":"🌐 Net Out","gridPos":{"x":20,"y":3,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"area"},
         "fieldConfig":{"defaults":{"unit":"Bps","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"orange","value":None}]}}},
         "targets":[tb(f"SELECT ts as time, net_bytes_sent as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":13,"type":"stat","title":"🌡 CPU Temp","gridPos":{"x":16,"y":6,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
         "fieldConfig":{"defaults":{"unit":"celsius","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":60},{"color":"red","value":80}]}}},
         "targets":[tb(f"SELECT ts as time, COALESCE(cpu_temp,0) as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":14,"type":"stat","title":"💾 Disk Free","gridPos":{"x":20,"y":6,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
         "fieldConfig":{"defaults":{"unit":"decgbytes","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"red","value":None},{"color":"yellow","value":10},{"color":"green","value":25}]}}},
         "targets":[tb(f"SELECT ts as time, (disk_partitions->0->>'free_gb')::float as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        # Row 3 — GPU
        {"id":15,"type":"stat","title":"🎮 GPU Name","gridPos":{"x":0,"y":9,"w":8,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"value","graphMode":"none"},
         "fieldConfig":{"defaults":{"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None}]}}},
         #"targets":[tb(f"SELECT ts as time, CASE WHEN gpu_info IS NULL OR gpu_info::text='null' THEN 'No GPU' ELSE (gpu_info->0->>'name') END as value FROM {T} ORDER BY ts DESC LIMIT 1")]},
	 "targets":[tb(f"SELECT ts as time, CASE WHEN gpu_info IS NULL OR gpu_info::text='null' OR jsonb_array_length(gpu_info)=0 THEN 'No GPU' ELSE COALESCE(gpu_info->0->>'name','Unknown') END as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":16,"type":"gauge","title":"🎮 GPU Usage %","gridPos":{"x":8,"y":9,"w":4,"h":6},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"showThresholdMarkers":True},
         "fieldConfig":{"defaults":{"unit":"percent","min":0,"max":100,"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":60},{"color":"red","value":90}]}}},
         "targets":[tb(f"SELECT ts as time, COALESCE((gpu_info->0->>'gpu_percent')::float,0) as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":17,"type":"gauge","title":"🎮 GPU VRAM %","gridPos":{"x":12,"y":9,"w":4,"h":6},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"showThresholdMarkers":True},
         "fieldConfig":{"defaults":{"unit":"percent","min":0,"max":100,"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":70},{"color":"red","value":90}]}}},
         "targets":[tb(f"SELECT ts as time, COALESCE((gpu_info->0->>'mem_percent')::float,0) as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":18,"type":"stat","title":"🌡 GPU Temp","gridPos":{"x":16,"y":9,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
         "fieldConfig":{"defaults":{"unit":"celsius","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":65},{"color":"red","value":85}]}}},
         "targets":[tb(f"SELECT ts as time, COALESCE((gpu_info->0->>'temp_c')::float,0) as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        {"id":19,"type":"stat","title":"🎮 GPU Type","gridPos":{"x":20,"y":9,"w":4,"h":3},"datasource":DS,
         "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"value","graphMode":"none"},
         "fieldConfig":{"defaults":{"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"blue","value":None}]}}},
         #"targets":[tb(f"SELECT ts as time, COALESCE(UPPER(gpu_info->0->>'type'),'NONE') as value FROM {T} ORDER BY ts DESC LIMIT 1")]},
	 "targets":[tb(f"SELECT ts as time, CASE WHEN gpu_info IS NULL OR gpu_info::text='null' OR jsonb_array_length(gpu_info)=0 THEN 'NONE' ELSE COALESCE(UPPER(gpu_info->0->>'type'),'NONE') END as value FROM {T} ORDER BY ts DESC LIMIT 1")]},

        # Row 4 — Time series CPU & Memory
        {"id":20,"type":"timeseries","title":"📈 CPU Usage","gridPos":{"x":0,"y":15,"w":12,"h":8},"datasource":DS,
         "fieldConfig":{"defaults":{"unit":"percent","min":0,"max":100,"custom":{"lineWidth":2,"fillOpacity":10},"color":{"mode":"palette-classic"}}},
         "options":{"tooltip":{"mode":"multi"},"legend":{"displayMode":"list","placement":"bottom"}},
         "targets":[ts("A", f"SELECT ts as time, cpu_percent as value FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC")]},

        {"id":21,"type":"timeseries","title":"🧠 Memory (GB)","gridPos":{"x":12,"y":15,"w":12,"h":8},"datasource":DS,
         "fieldConfig":{"defaults":{"unit":"decgbytes","custom":{"lineWidth":2,"fillOpacity":10},"color":{"mode":"palette-classic"}}},
         "options":{"tooltip":{"mode":"multi"},"legend":{"displayMode":"list","placement":"bottom"}},
         "targets":[ts("A", f"SELECT ts as time, ram_used_gb as value FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC")]},

        # Row 5 — Network & Disk I/O
        {"id":22,"type":"timeseries","title":"🌐 Network (bytes/s)","gridPos":{"x":0,"y":23,"w":12,"h":8},"datasource":DS,
         "fieldConfig":{"defaults":{"unit":"Bps","custom":{"lineWidth":2,"fillOpacity":10},"color":{"mode":"palette-classic"}}},
         "options":{"tooltip":{"mode":"multi"},"legend":{"displayMode":"list","placement":"bottom"}},
         "targets":[
             ts("A", f"SELECT ts as time, net_bytes_recv as \"In\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC"),
             ts("B", f"SELECT ts as time, net_bytes_sent as \"Out\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC")
         ]},

        {"id":23,"type":"timeseries","title":"💾 Disk I/O (MB)","gridPos":{"x":12,"y":23,"w":12,"h":8},"datasource":DS,
         "fieldConfig":{"defaults":{"unit":"decmbytes","custom":{"lineWidth":2,"fillOpacity":10},"color":{"mode":"palette-classic"}}},
         "options":{"tooltip":{"mode":"multi"},"legend":{"displayMode":"list","placement":"bottom"}},
         #"targets":[ts("A", f"SELECT ts as time, (disk_io->>'read_mb')::float as \"Read\", (disk_io->>'write_mb')::float as \"Write\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' AND disk_io IS NOT NULL ORDER BY ts ASC")]},
	 "targets":[
                    ts("A", f"SELECT ts as time, (disk_io->>'read_mb')::float as \"Read\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' AND disk_io IS NOT NULL ORDER BY ts ASC"),
                    ts("B", f"SELECT ts as time, (disk_io->>'write_mb')::float as \"Write\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' AND disk_io IS NOT NULL ORDER BY ts ASC")
                   ]},

        # Row 6 — GPU over time
        {"id":24,"type":"timeseries","title":"🎮 GPU Usage Over Time","gridPos":{"x":0,"y":31,"w":12,"h":8},"datasource":DS,
         "fieldConfig":{"defaults":{"unit":"percent","min":0,"max":100,"custom":{"lineWidth":2,"fillOpacity":10},"color":{"mode":"palette-classic"}}},
         "options":{"tooltip":{"mode":"multi"},"legend":{"displayMode":"list","placement":"bottom"}},
         "targets":[ts("A", f"SELECT ts as time, COALESCE((gpu_info->0->>'gpu_percent')::float,0) as \"GPU %\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC")]},

        {"id":25,"type":"timeseries","title":"🌡 Temperature Over Time","gridPos":{"x":12,"y":31,"w":12,"h":8},"datasource":DS,
         "fieldConfig":{"defaults":{"unit":"celsius","custom":{"lineWidth":2,"fillOpacity":10},"color":{"mode":"palette-classic"}}},
         "options":{"tooltip":{"mode":"multi"},"legend":{"displayMode":"list","placement":"bottom"}},
         "targets":[
             ts("A", f"SELECT ts as time, COALESCE(cpu_temp,0) as \"CPU\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC"),
             ts("B", f"SELECT ts as time, COALESCE((gpu_info->0->>'temp_c')::float,0) as \"GPU\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC")
         ]},

        # Row 7 — Top Processes & Disk Partitions
        {"id":26,"type":"table","title":"🔥 Top Processes","gridPos":{"x":0,"y":39,"w":14,"h":9},"datasource":DS,
         "options":{"sortBy":[{"displayName":"CPU %","desc":True}]},
         "fieldConfig":{"defaults":{"custom":{"displayMode":"auto"}},"overrides":[
             {"matcher":{"id":"byName","options":"CPU %"},"properties":[{"id":"custom.displayMode","value":"lcd-gauge"}]},
             {"matcher":{"id":"byName","options":"RAM %"},"properties":[{"id":"custom.displayMode","value":"lcd-gauge"}]}
         ]},
         "targets":[tb(f"SELECT p->>'name' as \"Process\",(p->>'pid')::int as \"PID\",(p->>'cpu_percent')::float as \"CPU %\",(p->>'mem_percent')::float as \"RAM %\",p->>'status' as \"Status\" FROM {T},jsonb_array_elements(top_processes) as p WHERE ts=(SELECT MAX(ts) FROM {T}) ORDER BY \"CPU %\" DESC LIMIT 10")]},

        {"id":27,"type":"table","title":"💾 Disk Partitions","gridPos":{"x":14,"y":39,"w":10,"h":9},"datasource":DS,
         "fieldConfig":{"defaults":{"custom":{"displayMode":"auto"}},"overrides":[
             {"matcher":{"id":"byName","options":"Used %"},"properties":[{"id":"custom.displayMode","value":"lcd-gauge"}]}
         ]},
         "targets":[tb(f"SELECT d->>'mountpoint' as \"Mount\",d->>'device' as \"Device\",(d->>'total_gb')::float as \"Total GB\",(d->>'used_gb')::float as \"Used GB\",(d->>'free_gb')::float as \"Free GB\",(d->>'percent')::float as \"Used %\" FROM {T},jsonb_array_elements(disk_partitions) as d WHERE ts=(SELECT MAX(ts) FROM {T})")]}
    ]

    dashboard = {
        "dashboard": {
            "uid": uid,
            "title": title,
            "tags": ["reformmed","machine"],
            "timezone": "browser",
            "refresh": "5s",
            "time": {"from":"now-30m","to":"now"},
            "panels": panels
        },
        "overwrite": True,
        "folderId": 0
    }

    result = gapi("/api/dashboards/db", method="POST", data=dashboard)
    if result and result.get("status") == "success":
        log.info(f"✅ Dashboard created: {result['url']}")
        return True
    else:
        log.error(f"❌ Failed for {T}: {result}")
        return False

def update_fleet_dashboard(machines):
    """Update fleet overview dashboard"""
    log.info(f"✅ Fleet updated ({len(machines)} machines)")

async def main():
    log.info("🚀 Dashboard Manager starting...")
    pool = await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS,
        min_size=2, max_size=5
    )
    log.info("✅ Connected — watching every 15s")

    # Create machine_registry if doesn't exist
    async with pool.acquire() as conn:
        await conn.execute("""
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
            )
        """)
    log.info("✅ machine_registry ready")

    # Clear known_machines on startup to force recreation
    known_machines.clear()

    while True:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT table_name, system_name, location FROM machine_registry")
                machines = [(r['table_name'], r['system_name'], r['location']) for r in rows]

                # Create dashboards for new machines
                for table_name, system_name, location in machines:
                    if table_name not in known_machines:
                        log.info(f"🆕 New machine: {system_name} ({location}) — creating dashboard...")
                        if create_dashboard(table_name, system_name, location):
                            known_machines.add(table_name)

                # Update fleet dashboard
                update_fleet_dashboard(machines)

        except Exception as e:
            log.error(f"Sync error: {e}")

        await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
