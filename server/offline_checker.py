"""
REFORMMED Alert Checker — Simple version reading from environment variables
"""
import asyncio, logging, smtplib, os
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ALERT] %(message)s")
log = logging.getLogger("checker")

DB_HOST = os.getenv("POSTGRES_HOST", "reformmed_postgres")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "monitor_machine")
DB_USER = os.getenv("POSTGRES_USER", "reformmed")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "monitor2345")

async def main():
    log.info("🚀 Alert Checker starting...")
    
    pool = await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS,
        min_size=2, max_size=5
    )
    
    log.info("✅ Connected to database")
    
    while True:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM machine_registry")
                log.info(f"Checking {len(rows)} machines...")
            
            await asyncio.sleep(int(os.getenv("CHECK_INTERVAL_SECS", "3")))
        except Exception as e:
            log.error(f"Check error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
