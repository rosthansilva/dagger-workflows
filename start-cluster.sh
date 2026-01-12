#!/bin/bash

LOG_FILE="/tmp/cluster.log"
PID_FILE="/tmp/cluster.pid"

echo "🧹 Limpando cache local..."
dagger core engine local-cache prune

echo "🚀 Iniciando Cluster K3s (Gateway)..."

nohup dagger call kns gateway up \
  --ports 6443:6443 \
  --ports 80:80 \
  --ports 443:443 

PID=$!
echo $PID > "$PID_FILE"

echo "✅ Cluster rodando em background (PID: $PID)."
echo "📄 Logs estão sendo escritos em: $LOG_FILE"
echo "OBS: Use './stop-cluster.sh' para desligar."