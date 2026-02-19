"""
REFORMMED Monitor API — Receives metrics from agents
"""
from fastapi import FastAPI, HTTPException, Header, Request
from datetime import datetime, timezone
import asyncpg, logging, os

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("api")

app = FastAPI(title="REFORMMED Monitor API")

DB_HOST = os.getenv("POSTGRES_HOST", "reformmed_postgres")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "monitor_machine")
DB_USER = os.getenv("POSTGRES_USER", "reformmed")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "monitor2345")
API_SECRET = os.getenv("API_SECRET", "")

pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS,
        min_size=5, max_size=20
    )
    log.info(f"✅ Connected to database at {DB_HOST}")

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.post("/register")
async def register(request: Request, x_api_key: str = Header(...)):
    if x_api_key != API_SECRET:
        raise HTTPException(401, "Invalid API key")
    
    data = await request.json()
    system_name = data.get("system_name")
    location = data.get("location")
    
    if not system_name or not location:
        raise HTTPException(400, "system_name and location required")
    
    table_name = f"machine_{system_name.lower().replace('-', '_').replace(' ', '_')}_{location.lower().replace('-', '_').replace(' ', '_')}"
    
    async with pool.acquire() as conn:
        # Create registry if not exists
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
        
        # Register machine
        await conn.execute("""
            INSERT INTO machine_registry (system_name, location, table_name, os_type, hostname, public_ip, last_seen, status)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), 'online')
            ON CONFLICT (table_name) DO UPDATE 
            SET last_seen=NOW(), status='online', os_type=$4, hostname=$5, public_ip=$6
        """, system_name, location, table_name, data.get("os_type"), data.get("hostname"), data.get("public_ip"))
        
        # Create metrics table
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                ts TIMESTAMPTZ DEFAULT NOW(),
                cpu_percent FLOAT,
                cpu_per_core JSONB,
                cpu_freq_mhz FLOAT,
                cpu_temp FLOAT,
                ram_total_gb FLOAT,
                ram_used_gb FLOAT,
                ram_percent FLOAT,
                swap_total_gb FLOAT,
                swap_used_gb FLOAT,
                swap_percent FLOAT,
                gpu_info JSONB,
                disk_partitions JSONB,
                disk_io JSONB,
                net_bytes_sent BIGINT,
                net_bytes_recv BIGINT,
                net_packets_sent BIGINT,
                net_packets_recv BIGINT,
                public_ip TEXT,
                top_processes JSONB,
                uptime_seconds FLOAT,
                boot_time TIMESTAMPTZ,
                os_version TEXT,
                hostname TEXT,
                status TEXT
            )
        """)
        await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_ts ON {table_name}(ts DESC)")
    
    return {"table_name": table_name}

@app.post("/metrics")
async def metrics(request: Request, x_api_key: str = Header(...)):
    if x_api_key != API_SECRET:
        raise HTTPException(401, "Invalid API key")
    
    data = await request.json()
    table_name = data.get("table_name")
    
    if not table_name:
        raise HTTPException(400, "table_name required")
    
    async with pool.acquire() as conn:
        # Update registry
        await conn.execute("""
            UPDATE machine_registry 
            SET last_seen=NOW(), status='online', public_ip=$2, hostname=$3
            WHERE table_name=$1
        """, table_name, data.get("public_ip"), data.get("hostname"))
        
        # Insert metrics
        await conn.execute(f"""
            INSERT INTO {table_name} (
                cpu_percent, cpu_per_core, cpu_freq_mhz, cpu_temp,
                ram_total_gb, ram_used_gb, ram_percent,
                swap_total_gb, swap_used_gb, swap_percent,
                gpu_info, disk_partitions, disk_io,
                net_bytes_sent, net_bytes_recv, net_packets_sent, net_packets_recv,
                public_ip, top_processes, uptime_seconds, boot_time, os_version, hostname, status
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24
            )
        """, 
        data.get("cpu_percent"), data.get("cpu_per_core"), data.get("cpu_freq_mhz"), data.get("cpu_temp"),
        data.get("ram_total_gb"), data.get("ram_used_gb"), data.get("ram_percent"),
        data.get("swap_total_gb"), data.get("swap_used_gb"), data.get("swap_percent"),
        data.get("gpu_info"), data.get("disk_partitions"), data.get("disk_io"),
        data.get("net_bytes_sent"), data.get("net_bytes_recv"), data.get("net_packets_sent"), data.get("net_packets_recv"),
        data.get("public_ip"), data.get("top_processes"), data.get("uptime_seconds"), 
        data.get("boot_time"), data.get("os_version"), data.get("hostname"), data.get("status"))
    
    return {"status": "ok"}

@app.get("/machines")
async def list_machines(x_api_key: str = Header(...)):
    if x_api_key != API_SECRET:
        raise HTTPException(401, "Invalid API key")
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM machine_registry ORDER BY id")
        return [dict(r) for r in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
