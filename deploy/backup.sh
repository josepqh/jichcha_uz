#!/bin/sh
# Daily PostgreSQL backups: custom-format pg_dump into /backups, keeping BACKUP_KEEP_DAYS days.
# Runs in the db-backup compose service. Restore: see README ("Backups").
set -eu

KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"

while true; do
    stamp="$(date -u +%Y%m%d-%H%M%S)"
    target="/backups/${PGDATABASE}-${stamp}.dump"
    # Write under a temporary name so a half-written dump never looks like a backup.
    if pg_dump --format=custom --no-owner --file="${target}.part"; then
        mv "${target}.part" "${target}"
        echo "backup ok: ${target} ($(du -h "${target}" | cut -f1))"
    else
        rm -f "${target}.part"
        echo "backup FAILED at ${stamp}" >&2
    fi
    find /backups -name "*.dump" -type f -mtime "+${KEEP_DAYS}" -print -delete
    sleep "${INTERVAL}"
done
