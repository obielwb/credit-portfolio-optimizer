#!/usr/bin/env bash
# Start a background performance benchmark with a dedicated log.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPTIMIZER_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${OPTIMIZER_ROOT}"

SESSION_ID="$(date +%Y-%m-%d_%H-%M-%S)"
OUT_BASE="${OPTIMIZER_ROOT}/reports/performance"
LOG_DIR="${OUT_BASE}/${SESSION_ID}"
mkdir -p "${LOG_DIR}"

LOG_FILE="${LOG_DIR}/run.log"
PID_FILE="${LOG_DIR}/perf.pid"

echo "Iniciando benchmark em background..."
echo "  Log: ${LOG_FILE}"
echo "  PID file: ${PID_FILE}"

nohup python3 tools/run_perf_reports.py \
  --output-dir "${OUT_BASE}" \
  > "${LOG_FILE}" 2>&1 &

echo $! > "${PID_FILE}"
echo "PID: $(cat "${PID_FILE}")"
echo "Acompanhe: tail -f ${LOG_FILE}"
