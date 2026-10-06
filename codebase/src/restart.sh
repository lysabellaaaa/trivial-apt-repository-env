#!/bin/bash
set -euo pipefail
trap 'echo "Startup failed; inspect /var/log/nginx/error.log" >&2' ERR
nginx -t -c /app/nginx.conf
# Reload a running server; otherwise create the initial NGINX master process.
if [[ -s /run/nginx.pid ]] && kill -0 "$(cat /run/nginx.pid)" 2>/dev/null; then
    nginx -s reload -c /app/nginx.conf
else
    nginx -c /app/nginx.conf
fi
# Success requires the generated catalog to be reachable, not merely a live NGINX process.
curl --fail --silent --retry 10 --retry-connrefused --retry-delay 1 http://localhost:8080/Packages.gz > /dev/null
