#!/bin/bash

# Source env vars dari host directory
# Source env vars dari host directory
if [ -f "../host/.env" ]; then
    set -a
    source "../host/.env"
    set +a
else
    echo "Error: ../host/.env tidak ditemukan."
    exit 1
fi

# Jalankan script python
python3 client-post.py
