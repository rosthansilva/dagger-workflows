#!/bin/bash

PID_FILE="cluster.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  Arquivo $PID_FILE não encontrado. O cluster está rodando?"
    exit 1
fi

PID=$(cat "$PID_FILE")

echo "🛑 Parando o Cluster (PID: $PID)..."
kill $PID

# Remove o arquivo de PID
rm "$PID_FILE"

echo "👋 Cluster desligado."