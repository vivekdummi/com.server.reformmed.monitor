"""
REFORMMED Monitor - FastAPI Server
Receives metrics from agents, stores in PostgreSQL, handles machine registration.
"""

import os
import re
import json
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("reformmed-server")

DB_HOST    = os.getenv("DB_HOST", "localhost")
DB_PORT    = int(os.getenv("DB_PORT", "5432"))
DB_USER    = os.getenv("DB_USER", "reformmed")
DB_PASS    = os.getenv("DB_PASS", "reformmed")
DB_NAME    = os.getenv("DB_NAME", "reformmed_monitor")
API_SECRET = os.getenv("API_SECRET", "reformmed-secret-key")

db_pool: Optional[asyncpg.Pool] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    log.info("Connecting to PostgreSQL...")
    db_pool = await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME, min_size=5, max_size=20
    )
    await ensure_registry_table()
    log.info("✅ Server ready")
    yield
    await db_pool.close()

app = FastAPI(title="REFORMMED Monitor Server", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class RegisterPayload(BaseModel):
    system_name: str
    location: str
    os_type: str
    hostname: str
    public_ip: Optional[str] = None

class MetricsPayload(BaseModel):
    system_name: str
    location: str
    timestamp: str
    cpu_percent: float
    cpu_per_core: list[float]
    cpu_freq_mhz: float
    cpu_temp: Optional[float] = None
    ram_total_gb: float
    ram_used_gb: float
    ram_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_percent: float
    gpu_info: Optional[list[dict]] = None
    disk_partitions: list[dict]
    disk_io: Optional[dict] = None
    net_bytes_sent: float
    net_bytes_recv: float
    net_packets_sent: float
    net_packets_recv: float
    public_ip: Optional[str] = None
    top_processes: list[dict]
    uptime_seconds: float
    boot_time: str
    os_version: str
    hostname: str
    status: str = "online"

def safe_table_name(system_name: str, location: str) -> str:
    raw = f"machine_{system_name}_{location}"
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw).lower()[:60]

async def ensure_registry_table():
    async with db_pool.acquire() as conn:
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

async def ensure_machine_table(table_name: str, conn):
    await conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGSERIAL PRIMARY KEY,
            ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            cpu_percent FLOAT, cpu_per_core JSONB, cpu_freq_mhz FLOAT, cpu_temp FLOAT,
            ram_total_gb FLOAT, ram_used_gb FLOAT, ram_percent FLOAT,
            swap_total_gb FLOAT, swap_used_gb FLOAT, swap_percent FLOAT,
            gpu_info JSONB, disk_partitions JSONB, disk_io JSONB,
            net_bytes_sent FLOAT, net_bytes_recv FLOAT,
            net_packets_sent FLOAT, net_packets_recv FLOAT,
            public_ip TEXT, top_processes JSONB, uptime_seconds FLOAT,
            boot_time TEXT, os_version TEXT, hostname TEXT, status TEXT
        )
    """)
    await conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_ts ON {table_name} (ts DESC)
    """)

def verify_secret(x_api_key: Optional[str]):
    if x_api_key != API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.post("/register")
async def register_machine(payload: RegisterPayload, x_api_key: Optional[str] = Header(None)):
    verify_secret(x_api_key)
    table_name = safe_table_name(payload.system_name, payload.location)
    async with db_pool.acquire() as conn:
        await ensure_machine_table(table_name, conn)
        existing = await conn.fetchrow("SELECT id FROM machine_registry WHERE table_name=$1", table_name)
        if existing:
            await conn.execute("""
                UPDATE machine_registry SET os_type=$1, hostname=$2, public_ip=$3,
                last_seen=NOW(), status='online' WHERE table_name=$4
            """, payload.os_type, payload.hostname, payload.public_ip, table_name)
        else:
            await conn.execute("""
                INSERT INTO machine_registry (system_name, location, table_name, os_type, hostname, public_ip, status)
                VALUES ($1,$2,$3,$4,$5,$6,'online')
            """, payload.system_name, payload.location, table_name,
                payload.os_type, payload.hostname, payload.public_ip)
    log.info(f"Registered: {table_name}")
    return {"status": "registered", "table_name": table_name}

@app.post("/metrics")
async def receive_metrics(payload: MetricsPayload, x_api_key: Optional[str] = Header(None)):
    verify_secret(x_api_key)
    table_name = safe_table_name(payload.system_name, payload.location)
    async with db_pool.acquire() as conn:
        await ensure_machine_table(table_name, conn)
        await conn.execute(f"""
            INSERT INTO {table_name} (
                ts, cpu_percent, cpu_per_core, cpu_freq_mhz, cpu_temp,
                ram_total_gb, ram_used_gb, ram_percent, swap_total_gb, swap_used_gb, swap_percent,
                gpu_info, disk_partitions, disk_io,
                net_bytes_sent, net_bytes_recv, net_packets_sent, net_packets_recv,
                public_ip, top_processes, uptime_seconds, boot_time, os_version, hostname, status
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25)
        """,
            datetime.fromisoformat(payload.timestamp),
            payload.cpu_percent, json.dumps(payload.cpu_per_core), payload.cpu_freq_mhz, payload.cpu_temp,
            payload.ram_total_gb, payload.ram_used_gb, payload.ram_percent,
            payload.swap_total_gb, payload.swap_used_gb, payload.swap_percent,
            json.dumps(payload.gpu_info) if payload.gpu_info else None,
            json.dumps(payload.disk_partitions),
            json.dumps(payload.disk_io) if payload.disk_io else None,
            payload.net_bytes_sent, payload.net_bytes_recv,
            payload.net_packets_sent, payload.net_packets_recv,
            payload.public_ip, json.dumps(payload.top_processes),
            payload.uptime_seconds, payload.boot_time, payload.os_version,
            payload.hostname, payload.status,
        )
        await conn.execute("""
            UPDATE machine_registry SET last_seen=NOW(), status='online', public_ip=$1 WHERE table_name=$2
        """, payload.public_ip, table_name)
    return {"status": "ok"}

@app.get("/machines")
async def list_machines(x_api_key: Optional[str] = Header(None)):
    verify_secret(x_api_key)
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT system_name, location, table_name, os_type,
                   hostname, public_ip, registered_at, last_seen, status
            FROM machine_registry ORDER BY system_name
        """)
    return [dict(r) for r in rows]

@app.get("/machines/{table_name}/latest")
async def get_latest(table_name: str, x_api_key: Optional[str] = Header(None)):
    verify_secret(x_api_key)
    clean = re.sub(r"[^a-z0-9_]", "", table_name)
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {clean} ORDER BY ts DESC LIMIT 1")
    if not row:
        raise HTTPException(404, "No data found")
    return dict(row)

@app.get("/machines/{table_name}/history")
async def get_history(table_name: str, minutes: int = 60, x_api_key: Optional[str] = Header(None)):
    verify_secret(x_api_key)
    clean = re.sub(r"[^a-z0-9_]", "", table_name)
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT ts, cpu_percent, ram_percent, net_bytes_sent, net_bytes_recv, status
            FROM {clean}
            WHERE ts > NOW() - INTERVAL '{minutes} minutes'
            ORDER BY ts ASC
        """)
    return [dict(r) for r in rows]
