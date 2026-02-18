#!/bin/bash
# Sync machine_registry status/ip/hostname from latest metrics
docker exec reformmed_postgres psql -U reformmed -d monitor_machine -c "
  DO \$\$
  DECLARE
    rec RECORD;
    latest RECORD;
    tbl TEXT;
  BEGIN
    FOR rec IN SELECT table_name FROM machine_registry LOOP
      tbl := rec.table_name;
      BEGIN
        EXECUTE format('
          UPDATE machine_registry SET
            status = t.status,
            public_ip = t.public_ip,
            hostname = t.hostname,
            last_seen = t.ts
          FROM (SELECT status, public_ip, hostname, ts FROM %I ORDER BY ts DESC LIMIT 1) t
          WHERE machine_registry.table_name = %L
        ', tbl, tbl);
      EXCEPTION WHEN OTHERS THEN
        NULL;
      END;
    END LOOP;
  END;
  \$\$;
" > /dev/null 2>&1
