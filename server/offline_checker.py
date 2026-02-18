import os, json, asyncio, logging, smtplib, traceback
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncpg

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ALERT] %(message)s")
log = logging.getLogger("reformmed-alerts")

DB_HOST        = os.getenv("DB_HOST", "localhost")
DB_PORT        = int(os.getenv("DB_PORT", "5432"))
DB_USER        = os.getenv("DB_USER", "reformmed")
DB_PASS        = os.getenv("DB_PASS", "reformmed")
DB_NAME        = os.getenv("DB_NAME", "reformmed_monitor")
GMAIL_USER     = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
ALERT_TO       = os.getenv("ALERT_TO", "")
OFFLINE_AFTER_SECS  = int(os.getenv("OFFLINE_AFTER_SECS", "10"))
CHECK_INTERVAL_SECS = int(os.getenv("CHECK_INTERVAL_SECS", "3"))
CPU_ALERT_THRESH    = float(os.getenv("CPU_ALERT_THRESH", "90"))
RAM_ALERT_THRESH    = float(os.getenv("RAM_ALERT_THRESH", "90"))
DISK_ALERT_THRESH   = float(os.getenv("DISK_ALERT_THRESH", "85"))
TEMP_ALERT_THRESH   = float(os.getenv("TEMP_ALERT_THRESH", "80"))

# IST = UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

machine_states: dict = {}
alert_cooldown: dict = {}
COOLDOWN_MINUTES = 10

def now_ist():
    return datetime.now(IST)

def fmt_ist(dt=None):
    if dt is None:
        dt = now_ist()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(IST)
    else:
        dt = dt.astimezone(IST)
    return dt.strftime("%d %b %Y, %I:%M:%S %p IST")

def send_email(subject: str, body_html: str):
    if not GMAIL_USER or not GMAIL_APP_PASS or not ALERT_TO:
        log.warning("Gmail not configured — skipping alert")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"REFORMMED Monitor <{GMAIL_USER}>"
        msg["To"]      = ALERT_TO
        msg.attach(MIMEText(body_html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASS)
            s.sendmail(GMAIL_USER, ALERT_TO.split(","), msg.as_string())
        log.info(f"📧 Email sent: {subject}")
    except Exception as e:
        log.error(f"Email failed: {e}")

def should_alert(key: str, cooldown_min: int = None) -> bool:
    mins = cooldown_min if cooldown_min is not None else COOLDOWN_MINUTES
    last = alert_cooldown.get(key)
    if last and (now_ist() - last).total_seconds() < mins * 60:
        return False
    alert_cooldown[key] = now_ist()
    return True

def make_table_row(label, value, alt=False):
    bg = "#f9f9f9" if alt else "#ffffff"
    return f"""<tr style="background:{bg}">
      <td style="padding:10px 14px;color:#555;font-weight:600;width:150px;border-bottom:1px solid #eee">{label}</td>
      <td style="padding:10px 14px;color:#222;border-bottom:1px solid #eee">{value}</td>
    </tr>"""

def make_email_html(color, emoji, title, badge_text, rows: list, footer_note=""):
    rows_html = "".join(rows)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 0">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08)">

        <!-- Header -->
        <tr><td style="background:{color};padding:24px 30px">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <div style="font-size:22px;font-weight:700;color:#fff">{emoji} {title}</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.85);margin-top:4px">REFORMMED Infrastructure Monitor</div>
              </td>
              <td align="right">
                <span style="background:rgba(255,255,255,0.2);color:#fff;padding:6px 14px;border-radius:20px;font-size:13px;font-weight:600">{badge_text}</span>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:0">
          <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
            {rows_html}
          </table>
        </td></tr>

        <!-- Alert time -->
        <tr><td style="padding:16px 30px;background:#fafafa;border-top:1px solid #eee">
          <div style="font-size:12px;color:#888">
            ⏰ Alert generated at <strong>{fmt_ist()}</strong>
            {"<br>" + footer_note if footer_note else ""}
          </div>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:14px 30px;background:#f0f2f5;text-align:center">
          <div style="font-size:11px;color:#aaa">REFORMMED Monitor System · Auto-generated alert · Do not reply</div>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body></html>"""

async def ensure_registry(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS machine_registry (
                id SERIAL PRIMARY KEY,
                system_name TEXT NOT NULL,
                location TEXT NOT NULL,
                table_name TEXT NOT NULL UNIQUE,
                os_type TEXT, hostname TEXT, public_ip TEXT,
                registered_at TIMESTAMPTZ DEFAULT NOW(),
                last_seen TIMESTAMPTZ,
                status TEXT DEFAULT 'offline'
            )
        """)

async def check_machines(pool):
    async with pool.acquire() as conn:
        machines = await conn.fetch(
            "SELECT system_name, location, table_name, public_ip, last_seen, status FROM machine_registry"
        )

    now_utc = datetime.now(timezone.utc)

    for m in machines:
        tname    = m["table_name"]
        sname    = m["system_name"]
        location = m["location"]
        pub_ip   = m["public_ip"] or "Unknown"
        last_seen = m["last_seen"]

        if last_seen is None:
            continue

        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        seconds_ago = (now_utc - last_seen).total_seconds()
        current = "offline" if seconds_ago > OFFLINE_AFTER_SECS else "online"
        prev    = machine_states.get(tname, m["status"])

        # ── OFFLINE alert ─────────────────────────────────────────────────────
        if current == "offline" and prev == "online":
            machine_states[tname] = "offline"
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE machine_registry SET status='offline' WHERE table_name=$1", tname
                )
            body = make_email_html(
                "#c0392b", "🔴", f"Machine Offline — {sname}", "OFFLINE",
                [
                    make_table_row("System Name", f"<strong>{sname}</strong>"),
                    make_table_row("Location", location, True),
                    make_table_row("Public IP", pub_ip),
                    make_table_row("Last Seen", fmt_ist(last_seen), True),
                    make_table_row("Offline Since", f"{seconds_ago:.0f} seconds ago"),
                    make_table_row("OS Type", m.get('os_type','Unknown') or 'Unknown', True),
                ],
                "Check network connectivity or power status of the machine."
            )
            send_email(f"🔴 OFFLINE: {sname} ({location}) — {fmt_ist()}", body)
            log.warning(f"🔴 OFFLINE: {sname} ({location}) — {seconds_ago:.0f}s ago")

        # ── ONLINE alert ──────────────────────────────────────────────────────
        elif current == "online" and prev == "offline":
            machine_states[tname] = "online"
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE machine_registry SET status='online' WHERE table_name=$1", tname
                )
            body = make_email_html(
                "#27ae60", "🟢", f"Machine Online — {sname}", "ONLINE",
                [
                    make_table_row("System Name", f"<strong>{sname}</strong>"),
                    make_table_row("Location", location, True),
                    make_table_row("Public IP", pub_ip),
                    make_table_row("Restored At", fmt_ist(), True),
                ],
                "Machine is back and sending metrics normally."
            )
            send_email(f"🟢 ONLINE: {sname} ({location}) — {fmt_ist()}", body)
            log.info(f"🟢 ONLINE: {sname} ({location})")

        else:
            machine_states[tname] = current

        if current != "online":
            continue

        # ── Threshold checks ──────────────────────────────────────────────────
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT cpu_percent, ram_percent, cpu_temp, "
                    f"disk_partitions, ram_used_gb, ram_total_gb "
                    f"FROM {tname} ORDER BY ts DESC LIMIT 1"
                )
            if not row:
                continue

            def thresh_alert(metric, val, thresh_val, unit, cooldown_min=10):
                if val is not None and val >= thresh_val:
                    key = f"{tname}_{metric}_high"
                    if should_alert(key, cooldown_min):
                        pct = f"{val:.1f}{unit}"
                        body = make_email_html(
                            "#d35400", "⚠️", f"High {metric} — {sname}", f"{pct}",
                            [
                                make_table_row("System Name", f"<strong>{sname}</strong>"),
                                make_table_row("Location", location, True),
                                make_table_row("Metric", metric),
                                make_table_row("Current Value",
                                    f"<span style='color:#e74c3c;font-size:20px;font-weight:700'>{pct}</span>", True),
                                make_table_row("Threshold", f"{thresh_val:.1f}{unit}"),
                                make_table_row("Public IP", pub_ip, True),
                                make_table_row("Time (IST)", fmt_ist()),
                            ],
                            f"Sustained high {metric} may impact system performance."
                        )
                        send_email(
                            f"⚠️ HIGH {metric.upper()}: {sname} ({location}) — {pct} at {fmt_ist()}",
                            body
                        )
                        log.warning(f"⚠️ {metric} alert: {sname} = {pct}")

            thresh_alert("CPU",         row["cpu_percent"], CPU_ALERT_THRESH,  "%")
            thresh_alert("RAM",         row["ram_percent"], RAM_ALERT_THRESH,  "%")
            thresh_alert("Temperature", row["cpu_temp"],    TEMP_ALERT_THRESH, "°C")

            # Disk per partition
            if row["disk_partitions"]:
                parts = row["disk_partitions"] if isinstance(row["disk_partitions"], list) \
                        else json.loads(row["disk_partitions"])
                for p in parts:
                    pct = p.get("percent", 0)
                    mp  = p.get("mountpoint", "?")
                    dev = p.get("device", "")
                    # Skip snap loop devices, tmpfs, overlay — always 100% by design
                    if any(x in dev for x in ["/dev/loop", "tmpfs", "overlay", "shm"]):
                        continue
                    if any(x in mp for x in ["/snap/", "/run/", "/sys/", "/proc/"]):
                        continue
                    if pct >= DISK_ALERT_THRESH:
                        key = f"{tname}_disk_{mp}_high"
                        if should_alert(key):
                            body = make_email_html(
                                "#8e44ad", "💾", f"Disk Almost Full — {sname}", f"{pct:.1f}%",
                                [
                                    make_table_row("System Name", f"<strong>{sname}</strong>"),
                                    make_table_row("Location", location, True),
                                    make_table_row("Mount Point", mp),
                                    make_table_row("Device", p.get("device","?"), True),
                                    make_table_row("Usage",
                                        f"<span style='color:#e74c3c;font-size:20px;font-weight:700'>{pct:.1f}%</span>"),
                                    make_table_row("Used / Total",
                                        f"{p.get('used_gb',0):.1f} GB / {p.get('total_gb',0):.1f} GB", True),
                                    make_table_row("Free", f"{p.get('free_gb',0):.1f} GB"),
                                    make_table_row("Time (IST)", fmt_ist(), True),
                                ]
                            )
                            send_email(
                                f"💾 DISK FULL: {sname} {mp} — {pct:.1f}% at {fmt_ist()}",
                                body
                            )

        except Exception as e:
            log.error(f"Threshold check error {tname}: {e}")
            traceback.print_exc()

async def main():
    log.info(f"🚀 REFORMMED Checker starting")
    log.info(f"   Offline after  : {OFFLINE_AFTER_SECS}s")
    log.info(f"   Check interval : {CHECK_INTERVAL_SECS}s")
    log.info(f"   Alerts → {ALERT_TO or '(not set)'}")
    log.info(f"   Thresholds: CPU>{CPU_ALERT_THRESH}% RAM>{RAM_ALERT_THRESH}% Disk>{DISK_ALERT_THRESH}% Temp>{TEMP_ALERT_THRESH}°C")

    pool = await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASS, database=DB_NAME, min_size=2, max_size=5
    )
    log.info("✅ DB connected")
    await ensure_registry(pool)
    log.info("✅ Ready — monitoring every 3 seconds")

    cycle = 0
    while True:
        cycle += 1
        try:
            await check_machines(pool)
        except Exception as e:
            log.error(f"Cycle {cycle} error: {e}")
            traceback.print_exc()
        await asyncio.sleep(CHECK_INTERVAL_SECS)

if __name__ == "__main__":
    asyncio.run(main())
