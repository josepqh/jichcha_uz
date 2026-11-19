#!/bin/sh
# Daily PostgreSQL backups: custom-format pg_dump into /backups, keeping BACKUP_KEEP_DAYS days.
# With BACKUP_REMOTE set (an rclone remote such as "offsite:universe-backups"), each dump is also
# copied off the server and remote copies older than BACKUP_REMOTE_KEEP_DAYS are removed.
# Runs in the db-backup compose service. Restore: see README ("Backups").
set -eu

KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
REMOTE_KEEP_DAYS="${BACKUP_REMOTE_KEEP_DAYS:-30}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
REMOTE="${BACKUP_REMOTE:-}"

# Stop promptly on "docker compose stop": the long sleep runs in the background so the trap fires.
trap 'exit 0' TERM INT

while true; do
    stamp="$(date -u +%Y%m%d-%H%M%S)"
    target="/backups/${PGDATABASE}-${stamp}.dump"
    # Write under a temporary name so a half-written dump never looks like a backup.
    if pg_dump --format=custom --no-owner --file="${target}.part"; then
        mv "${target}.part" "${target}"
        echo "backup ok: ${target} ($(du -h "${target}" | cut -f1))"
        if [ -n "${REMOTE}" ]; then
            if rclone copy --quiet "${target}" "${REMOTE}"; then
                echo "off-site copy ok: ${REMOTE}"
                rclone delete --quiet --min-age "${REMOTE_KEEP_DAYS}d" --include "*.dump" "${REMOTE}" || true
            else
                echo "off-site copy FAILED (${REMOTE})" >&2
            fi
        fi
    else
        rm -f "${target}.part"
        echo "backup FAILED at ${stamp}" >&2
    fi
    find /backups -name "*.dump" -type f -mtime "+${KEEP_DAYS}" -print -delete
    sleep "${INTERVAL}" &
    wait $!
done
