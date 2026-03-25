#!/bin/bash
set -euo pipefail

echo "Starting mounts as child processes..."

( minikube mount /Users/dariusgherca/facultate/master1/sem1/cloudComputing/task-manager/envoy/envoy-config:/mnt/envoy-config ) &
PID_ENV=$!

( minikube mount /Users/dariusgherca/facultate/master1/sem1/cloudComputing/task-manager/login/certs:/etc/certs ) &
PID_CERTS=$!

cleanup() {
  echo "Stopping mount child processes..."
  kill "$PID_ENV" "$PID_CERTS" 2>/dev/null || true
  wait "$PID_ENV" "$PID_CERTS" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Mounts running. PIDs: $PID_ENV, $PID_CERTS"
wait