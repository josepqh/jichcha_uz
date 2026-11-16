# syntax=docker/dockerfile:1
# pg_dump + rclone for daily database backups with an optional off-site copy.
FROM postgres:18.1-alpine
RUN apk add --no-cache rclone
COPY --chmod=0555 backup.sh /backup.sh
ENTRYPOINT ["/bin/sh", "/backup.sh"]
