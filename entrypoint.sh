#!/bin/bash
# Entrypoint script for trix-hub
# Updates /etc/hosts with trix-server IP before starting the application

set -e

# Add trix-server to /etc/hosts if TRIX_SERVER_IP is provided
if [ -n "$TRIX_SERVER_IP" ]; then
    echo "[entrypoint] Adding trix-server.local -> $TRIX_SERVER_IP to /etc/hosts"

    # Remove any existing trix-server.local entries
    sed -i '/trix-server\.local/d' /etc/hosts 2>/dev/null || true

    # Add new entry (ensure newline before entry)
    echo "" >> /etc/hosts
    echo "$TRIX_SERVER_IP    trix-server.local" >> /etc/hosts
else
    echo "[entrypoint] TRIX_SERVER_IP not set, skipping /etc/hosts configuration"
fi

# Execute the main application command as the trixhub user
# Note: Using su (without -) to preserve environment variables like PYTHONUNBUFFERED
if [ "$#" -eq 0 ]; then
    # No command specified, start interactive shell
    cd /app
    exec su trixhub
else
    # Command specified, execute it
    # Use su without - to preserve environment variables
    cd /app
    exec su trixhub -c "exec $*"
fi
