import os, asyncio, logging, json, urllib.request, urllib.error, base64
import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [DASH] %(message)s")
log = logging.getLogger("dashboard-manager")

DB_HOST      = os.getenv("DB_HOST", "localhost")
DB_PORT      = int(os.getenv("DB_PORT", "5432"))
DB_USER      = os.getenv("DB_USER", "reformmed")
DB_PASS      = os.getenv("DB_PASS", "reformmed")
DB_NAME      = os.getenv("DB_NAME", "reformmed_monitor")
GRAFANA_URL  = os.getenv("GRAFANA_URL", "http://grafana:3000")
GRAFANA_USER = os.getenv("GRAFANA_USER", "admin")
GRAFANA_PASS = os.getenv("GRAFANA_PASS", "monitor2345")
DS_UID       = os.getenv("GRAFANA_DS_UID", "PCC52D03280B7034C")

known_machines = set()

def grafana_api(path, method="GET", data=None):
    creds = base64.b64encode(f"{GRAFANA_USER}:{GRAFANA_PASS}".encode()).decode()
    body  = json.dumps(data).encode() if data else None
    req   = urllib.request.Request(
        f"{GRAFANA_URL}{path}", data=body, method=method,
        headers={"Content-Type":"application/json","Authorization":f"Basic {creds}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        log.error(f"Grafana {method} {path} → {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        log.error(f"Grafana request error: {e}")
        return None

DS = {"type": "grafana-postgresql-datasource", "uid": DS_UID}

def p_stat(pid, title, sql, unit, color, x, y, w=4, h=3, mode="background"):
    steps_map = {
        "green":       [{"color":"green","value":None}],
        "blue":        [{"color":"blue","value":None}],
        "purple":      [{"color":"purple","value":None}],
        "orange":      [{"color":"orange","value":None}],
        "teal":        [{"color":"teal","value":None}],
        "dark-blue":   [{"color":"dark-blue","value":None}],
        "semi-dark-green": [{"color":"semi-dark-green","value":None}],
    }
    return {
        "id":pid,"type":"stat","title":title,
        "gridPos":{"x":x,"y":y,"w":w,"h":h},
        "datasource":DS,
        "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":mode,"graphMode":"none","textMode":"auto"},
        "fieldConfig":{"defaults":{
            "unit":unit,"color":{"mode":"thresholds"},
            "thresholds":{"mode":"absolute","steps":steps_map.get(color,[{"color":color,"value":None}])}
        }},
        "targets":[{"refId":"A","rawSql":sql,"format":"table"}]
    }

def p_gauge(pid, title, sql, unit, x, y, w=4, h=6, mn=0, mx=100, steps=None):
    if steps is None:
        steps = [{"color":"green","value":None},{"color":"yellow","value":60},{"color":"orange","value":80},{"color":"red","value":90}]
    return {
        "id":pid,"type":"gauge","title":title,
        "gridPos":{"x":x,"y":y,"w":w,"h":h},
        "datasource":DS,
        "options":{"reduceOptions":{"calcs":["lastNotNull"]},"showThresholdMarkers":True,"showThresholdLabels":True,"minVizHeight":100},
        "fieldConfig":{"defaults":{
            "unit":unit,"min":mn,"max":mx,
            "color":{"mode":"thresholds"},
            "thresholds":{"mode":"absolute","steps":steps}
        }},
        "targets":[{"refId":"A","rawSql":sql,"format":"table"}]
    }

def p_ts(pid, title, targets, unit, x, y, w=12, h=8):
    return {
        "id":pid,"type":"timeseries","title":title,
        "gridPos":{"x":x,"y":y,"w":w,"h":h},
        "datasource":DS,
        "fieldConfig":{"defaults":{
            "unit":unit,
            "custom":{"lineWidth":2,"fillOpacity":10,"gradientMode":"opacity","spanNulls":True},
            "color":{"mode":"palette-classic"}
        }},
        "options":{
            "tooltip":{"mode":"multi","sort":"desc"},
            "legend":{"displayMode":"table","placement":"bottom","calcs":["mean","max","last"]}
        },
        "targets":[{"refId":r,"rawSql":s,"format":"time_series"} for r,s in targets]
    }

def p_table(pid, title, sql, x, y, w=12, h=9, overrides=None):
    return {
        "id":pid,"type":"table","title":title,
        "gridPos":{"x":x,"y":y,"w":w,"h":h},
        "datasource":DS,
        "options":{"sortBy":[{"displayName":"CPU %","desc":True}]},
        "fieldConfig":{"defaults":{"custom":{"displayMode":"auto","align":"auto"}},"overrides":overrides or []},
        "targets":[{"refId":"A","rawSql":sql,"format":"table"}]
    }

def machine_dashboard(sname, location, T):
    uid   = f"mach-{T}"[:40]
    title = f"{sname} — {location}"
    W30   = "WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC"

    panels = [
        # ── Row 1: Info (y=0) ────────────────────────────────────────────
        {   # Status from machine_registry
            "id":1,"type":"stat","title":"🟢 Status",
            "gridPos":{"x":0,"y":0,"w":4,"h":3},"datasource":DS,
            "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
            "fieldConfig":{"defaults":{"mappings":[{"type":"value","options":{
                "online": {"text":"🟢 ONLINE","color":"green","index":0},
                "offline":{"text":"🔴 OFFLINE","color":"red","index":1}
            }}],"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"red","value":None}]}}},
            "targets":[{"refId":"A","rawSql":f"SELECT NOW() as time, status FROM {T} ORDER BY ts DESC LIMIT 1","format":"table"}]
        },
        p_stat(2,  "⏱ Uptime",     f"SELECT NOW() as time, uptime_seconds as \"Uptime\" FROM {T} ORDER BY ts DESC LIMIT 1", "s",          "blue",          4,  0, 4, 3),
        p_stat(3,  "🌐 Public IP",  f"SELECT NOW() as time, COALESCE(public_ip, hostname) as \"IP\" FROM {T} ORDER BY ts DESC LIMIT 1",          "string",     "purple",        8,  0, 4, 3),
        p_stat(4,  "💻 Hostname",   f"SELECT NOW() as time, COALESCE(hostname, os_version) as \"Host\" FROM {T} ORDER BY ts DESC LIMIT 1",         "string",     "dark-blue",    12,  0, 4, 3),
        p_stat(5,  "📦 RAM Total",  f"SELECT NOW() as time, ram_total_gb as \"RAM\" FROM {T} ORDER BY ts DESC LIMIT 1",      "decgbytes",  "teal",         16,  0, 4, 3),
        p_stat(6,  "💿 Disk Total", f"SELECT NOW() as time, (disk_partitions->0->>'total_gb')::float as \"Disk\" FROM {T} ORDER BY ts DESC LIMIT 1", "decgbytes","semi-dark-green",20, 0, 4, 3),

        # ── Row 2: Gauges (y=3) ──────────────────────────────────────────
        p_gauge(7,  "CPU %",      f"SELECT NOW() as time, cpu_percent as \"CPU\" FROM {T} ORDER BY ts DESC LIMIT 1",  "percent", 0, 3, 4, 6),
        p_gauge(8,  "RAM %",      f"SELECT NOW() as time, ram_percent as \"RAM\" FROM {T} ORDER BY ts DESC LIMIT 1",  "percent", 4, 3, 4, 6),
        p_gauge(9,  "Disk %",     f"SELECT NOW() as time, (disk_partitions->0->>'percent')::float as \"Disk\" FROM {T} ORDER BY ts DESC LIMIT 1", "percent", 8, 3, 4, 6),
        p_gauge(10, "Swap %",     f"SELECT NOW() as time, swap_percent as \"Swap\" FROM {T} ORDER BY ts DESC LIMIT 1","percent",12, 3, 4, 6,
                steps=[{"color":"green","value":None},{"color":"yellow","value":40},{"color":"red","value":75}]),

        # Network + Temp stats (y=3, right side)
        {   "id":11,"type":"stat","title":"🌐 Net In",
            "gridPos":{"x":16,"y":3,"w":4,"h":3},"datasource":DS,
            "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"area"},
            "fieldConfig":{"defaults":{"unit":"Bps","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":1000000},{"color":"red","value":10000000}]}}},
            "targets":[{"refId":"A","rawSql":f"SELECT NOW() as time, net_bytes_recv as \"In\" FROM {T} ORDER BY ts DESC LIMIT 1","format":"table"}]
        },
        {   "id":12,"type":"stat","title":"🌐 Net Out",
            "gridPos":{"x":20,"y":3,"w":4,"h":3},"datasource":DS,
            "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"area"},
            "fieldConfig":{"defaults":{"unit":"Bps","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"orange","value":None},{"color":"red","value":10000000}]}}},
            "targets":[{"refId":"A","rawSql":f"SELECT NOW() as time, net_bytes_sent as \"Out\" FROM {T} ORDER BY ts DESC LIMIT 1","format":"table"}]
        },
        {   "id":13,"type":"stat","title":"🌡 CPU Temp",
            "gridPos":{"x":16,"y":6,"w":4,"h":3},"datasource":DS,
            "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
            "fieldConfig":{"defaults":{"unit":"celsius","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":60},{"color":"red","value":80}]}}},
            "targets":[{"refId":"A","rawSql":f"SELECT NOW() as time, COALESCE(cpu_temp,0) as \"Temp\" FROM {T} ORDER BY ts DESC LIMIT 1","format":"table"}]
        },
        {   "id":14,"type":"stat","title":"💾 Disk Free",
            "gridPos":{"x":20,"y":6,"w":4,"h":3},"datasource":DS,
            "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
            "fieldConfig":{"defaults":{"unit":"decgbytes","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"red","value":None},{"color":"yellow","value":10},{"color":"green","value":25}]}}},
            "targets":[{"refId":"A","rawSql":f"SELECT NOW() as time, (disk_partitions->0->>'free_gb')::float as \"Free\" FROM {T} ORDER BY ts DESC LIMIT 1","format":"table"}]
        },

        # ── Row 3: GPU (y=9) ─────────────────────────────────────────────
        {   "id":15,"type":"stat","title":"🎮 GPU Status",
            "gridPos":{"x":0,"y":9,"w":6,"h":3},"datasource":DS,
            "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"value","graphMode":"none"},
            "fieldConfig":{"defaults":{"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None}]}}},
            "targets":[{"refId":"A","rawSql":f"SELECT NOW() as time, CASE WHEN gpu_info IS NULL OR gpu_info::text='null' THEN 'No GPU' ELSE (gpu_info->0->>'name') END as \"GPU\" FROM {T} ORDER BY ts DESC LIMIT 1","format":"table"}]
        },
        p_gauge(16, "🎮 GPU Usage %",
            f"SELECT NOW() as time, COALESCE((gpu_info->0->>'gpu_percent')::float, 0) as \"GPU %\" FROM {T} ORDER BY ts DESC LIMIT 1",
            "percent", 6, 9, 6, 3,
            steps=[{"color":"green","value":None},{"color":"yellow","value":60},{"color":"red","value":90}]),
        p_gauge(17, "🎮 GPU VRAM %",
            f"SELECT NOW() as time, COALESCE((gpu_info->0->>'mem_percent')::float, 0) as \"VRAM %\" FROM {T} ORDER BY ts DESC LIMIT 1",
            "percent", 12, 9, 6, 3,
            steps=[{"color":"green","value":None},{"color":"yellow","value":70},{"color":"red","value":90}]),
        {   "id":18,"type":"stat","title":"🌡 GPU Temp",
            "gridPos":{"x":18,"y":9,"w":6,"h":3},"datasource":DS,
            "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"none"},
            "fieldConfig":{"defaults":{"unit":"celsius","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":65},{"color":"red","value":85}]}}},
            "targets":[{"refId":"A","rawSql":f"SELECT NOW() as time, COALESCE((gpu_info->0->>'temp_c')::float, 0) as \"GPU Temp\" FROM {T} ORDER BY ts DESC LIMIT 1","format":"table"}]
        },

        # ── Row 4: CPU + RAM time series (y=12) ──────────────────────────
        p_ts(19, "📈 CPU Usage & All Cores", [
            ("A", f"SELECT ts as time, cpu_percent as \"Total CPU %\" FROM {T} {W30}"),
            ("B", f"SELECT ts as time, (cpu_per_core->>0)::float as \"Core 0\" FROM {T} {W30}"),
            ("C", f"SELECT ts as time, (cpu_per_core->>1)::float as \"Core 1\" FROM {T} {W30}"),
            ("D", f"SELECT ts as time, (cpu_per_core->>2)::float as \"Core 2\" FROM {T} {W30}"),
            ("E", f"SELECT ts as time, (cpu_per_core->>3)::float as \"Core 3\" FROM {T} {W30}"),
        ], "percent", 0, 12),

        p_ts(20, "🧠 Memory (GB)", [
            ("A", f"SELECT ts as time, ram_used_gb as \"RAM Used\", ram_total_gb as \"RAM Total\" FROM {T} {W30}"),
            ("B", f"SELECT ts as time, swap_used_gb as \"Swap Used\" FROM {T} {W30}"),
        ], "decgbytes", 12, 12),

        # ── Row 5: Network + Disk IO (y=20) ──────────────────────────────
        p_ts(21, "🌐 Network Traffic (bytes/s)", [
            ("A", f"SELECT ts as time, net_bytes_recv as \"In\", net_bytes_sent as \"Out\" FROM {T} {W30}"),
        ], "Bps", 0, 20),

        p_ts(22, "💿 Disk I/O (MB)", [
            ("A", f"SELECT ts as time, (disk_io->>'read_mb')::float as \"Read MB\", (disk_io->>'write_mb')::float as \"Write MB\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' AND disk_io IS NOT NULL ORDER BY ts ASC"),
        ], "decmbytes", 12, 20),

        # ── Row 6: GPU time series (y=28) ────────────────────────────────
        p_ts(23, "🎮 GPU Usage Over Time", [
            ("A", f"SELECT ts as time, COALESCE((gpu_info->0->>'gpu_percent')::float,0) as \"GPU %\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' AND gpu_info IS NOT NULL ORDER BY ts ASC"),
            ("B", f"SELECT ts as time, COALESCE((gpu_info->0->>'mem_percent')::float,0) as \"VRAM %\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' AND gpu_info IS NOT NULL ORDER BY ts ASC"),
        ], "percent", 0, 28),

        p_ts(24, "🌡 Temperature Over Time", [
            ("A", f"SELECT ts as time, COALESCE(cpu_temp,0) as \"CPU Temp °C\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC"),
            ("B", f"SELECT ts as time, COALESCE((gpu_info->0->>'temp_c')::float,0) as \"GPU Temp °C\" FROM {T} WHERE ts >= NOW() - INTERVAL '30 minutes' ORDER BY ts ASC"),
        ], "celsius", 12, 28),

        # ── Row 7: Tables (y=36) ─────────────────────────────────────────
        p_table(25, "🔥 Top Processes (Live)", f"""
            SELECT p->>'name' as "Process",
                   (p->>'pid')::int as "PID",
                   (p->>'cpu_percent')::float as "CPU %",
                   (p->>'mem_percent')::float as "RAM %",
                   p->>'status' as "Status"
            FROM {T}, jsonb_array_elements(top_processes) as p
            WHERE ts=(SELECT MAX(ts) FROM {T})
            ORDER BY "CPU %" DESC
        """, 0, 36, 14, 9,
        overrides=[
            {"matcher":{"id":"byName","options":"CPU %"},"properties":[
                {"id":"custom.displayMode","value":"lcd-gauge"},
                {"id":"thresholds","value":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":30},{"color":"red","value":70}]}}
            ]},
            {"matcher":{"id":"byName","options":"RAM %"},"properties":[
                {"id":"custom.displayMode","value":"lcd-gauge"},
                {"id":"thresholds","value":{"mode":"absolute","steps":[{"color":"blue","value":None},{"color":"orange","value":5},{"color":"red","value":20}]}}
            ]}
        ]),

        p_table(26, "💾 Disk Partitions", f"""
            SELECT d->>'mountpoint' as "Mount",
                   d->>'device' as "Device",
                   d->>'fstype' as "FS",
                   (d->>'total_gb')::float as "Total GB",
                   (d->>'used_gb')::float as "Used GB",
                   (d->>'free_gb')::float as "Free GB",
                   (d->>'percent')::float as "Used %"
            FROM {T}, jsonb_array_elements(disk_partitions) as d
            WHERE ts=(SELECT MAX(ts) FROM {T})
        """, 14, 36, 10, 9,
        overrides=[
            {"matcher":{"id":"byName","options":"Used %"},"properties":[
                {"id":"custom.displayMode","value":"lcd-gauge"},
                {"id":"thresholds","value":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"yellow","value":60},{"color":"red","value":85}]}}
            ]}
        ]),
    ]

    return {
        "dashboard":{
            "uid": uid,
            "title": f"🖥 {title}",
            "tags": ["reformmed","machine",location.lower()],
            "timezone": "browser",
            "refresh": "1s",
            "time": {"from":"now-30m","to":"now"},
            "panels": panels
        },
        "overwrite": True,
        "folderId": 0
    }

def fleet_dashboard(machines):
    panels = []
    pid = 1

    for title, sql, color, x in [
        ("Total Machines", "SELECT NOW() as time, COUNT(*) as \"v\" FROM machine_registry", "blue", 0),
        ("🟢 Online",       "SELECT NOW() as time, COUNT(*) as \"v\" FROM machine_registry WHERE status='online'", "green", 4),
        ("🔴 Offline",      "SELECT NOW() as time, COUNT(*) as \"v\" FROM machine_registry WHERE status='offline'", "red", 8),
    ]:
        panels.append({
            "id":pid,"type":"stat","title":title,
            "gridPos":{"x":x,"y":0,"w":4,"h":3},"datasource":DS,
            "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background"},
            "fieldConfig":{"defaults":{"unit":"short","color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":[{"color":color,"value":None}]}}},
            "targets":[{"refId":"A","rawSql":sql,"format":"table"}]
        })
        pid += 1

    panels.append({
        "id":pid,"type":"table","title":"🖥 All Machines",
        "gridPos":{"x":0,"y":3,"w":24,"h":6},"datasource":DS,
        "options":{"sortBy":[{"displayName":"Status","desc":False}]},
        "fieldConfig":{"defaults":{"custom":{"displayMode":"auto"}},"overrides":[
            {"matcher":{"id":"byName","options":"Status"},"properties":[
                {"id":"custom.displayMode","value":"color-background"},
                {"id":"mappings","value":[{"type":"value","options":{
                    "online": {"text":"🟢 ONLINE","color":"green","index":0},
                    "offline":{"text":"🔴 OFFLINE","color":"red","index":1}
                }}]},
                {"id":"custom.width","value":150}
            ]},
            {"matcher":{"id":"byName","options":"Last Seen"},"properties":[{"id":"unit","value":"dateTimeAsLocal"}]}
        ]},
        "targets":[{"refId":"A","format":"table","rawSql":"""
            SELECT system_name as "Machine", location as "Location",
                   status as "Status", public_ip as "IP",
                   hostname as "Hostname", os_type as "OS",
                   EXTRACT(EPOCH FROM last_seen)*1000 as "Last Seen",
                   EXTRACT(EPOCH FROM NOW()-last_seen)::int as "Seconds Ago"
            FROM machine_registry ORDER BY status ASC, system_name ASC
        """}]
    })
    pid += 1

    # Mini stats per machine
    y = 9; x = 0
    for m in machines:
        T = m["table_name"]
        sname = m["system_name"]
        dash_uid = f"mach-{T}"[:40]
        for metric, sql, unit, color in [
            ("CPU %",  f"SELECT NOW() as time, cpu_percent as \"v\" FROM {T} ORDER BY ts DESC LIMIT 1",  "percent", [{"color":"green","value":None},{"color":"yellow","value":70},{"color":"red","value":90}]),
            ("RAM %",  f"SELECT NOW() as time, ram_percent as \"v\" FROM {T} ORDER BY ts DESC LIMIT 1",  "percent", [{"color":"green","value":None},{"color":"yellow","value":70},{"color":"red","value":90}]),
            ("Disk %", f"SELECT NOW() as time, (disk_partitions->0->>'percent')::float as \"v\" FROM {T} ORDER BY ts DESC LIMIT 1","percent",[{"color":"green","value":None},{"color":"yellow","value":70},{"color":"red","value":85}]),
        ]:
            panels.append({
                "id":pid,"type":"stat","title":f"{sname} — {metric}",
                "gridPos":{"x":x,"y":y,"w":8,"h":3},"datasource":DS,
                "options":{"reduceOptions":{"calcs":["lastNotNull"]},"colorMode":"background","graphMode":"area"},
                "fieldConfig":{"defaults":{"unit":unit,"min":0,"max":100,"color":{"mode":"thresholds"},"thresholds":{"mode":"absolute","steps":color}}},
                "targets":[{"refId":"A","rawSql":sql,"format":"table"}],
                "links":[{"title":f"Open {sname} dashboard","url":f"/d/{dash_uid}","targetBlank":False}]
            })
            pid += 1; x += 8
            if x >= 24: x = 0; y += 3

    return {
        "dashboard":{
            "uid":"reformmed-fleet",
            "title":"🚀 REFORMMED Fleet Overview",
            "tags":["reformmed","fleet"],
            "timezone":"browser",
            "refresh":"5s",
            "time":{"from":"now-1h","to":"now"},
            "panels":panels
        },
        "overwrite":True,
        "folderId":0
    }

async def sync_dashboards(pool):
    async with pool.acquire() as conn:
        machines = [dict(m) for m in await conn.fetch(
            "SELECT system_name, location, table_name, status FROM machine_registry ORDER BY system_name"
        )]
    current = {m["table_name"] for m in machines}
    new     = current - known_machines

    for m in machines:
        T = m["table_name"]
        if T in new:
            log.info(f"🆕 New machine: {m['system_name']} ({m['location']}) — creating dashboard...")
            dash   = machine_dashboard(m["system_name"], m["location"], T)
            result = grafana_api("/api/dashboards/db", "POST", dash)
            if result and result.get("status") == "success":
                log.info(f"✅ Dashboard created: /d/{dash['dashboard']['uid']}")
                known_machines.add(T)
            else:
                log.error(f"❌ Failed for {T}: {result}")
        else:
            known_machines.add(T)

    # Recreate fleet
    if machines:
        r = grafana_api("/api/dashboards/db", "POST", fleet_dashboard(machines))
        if r and r.get("status") == "success":
            log.info(f"✅ Fleet updated ({len(machines)} machines)")

async def main():
    log.info("🚀 Dashboard Manager starting...")
    pool = await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME, min_size=2, max_size=5
    )
    log.info("✅ Connected — watching every 15s")

    # Create machine_registry if it doesn't exist
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

    # Force recreate all dashboards on startup
    known_machines.clear()

    while True:
        try:
            await sync_dashboards(pool)
        except Exception as e:
            log.error(f"Sync error: {e}")
        await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())
# This line intentionally left blank
