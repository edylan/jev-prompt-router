#!/usr/bin/env bash
# Launch the dashboard for a given slice. Avoids long single-line commands.
#   ./eval/dashboard.sh dev      -> development split (191 rows)  -> eval/results/dev.jsonl
#   ./eval/dashboard.sh test     -> blind test split (737 rows)   -> eval/results/test.jsonl
#   ./eval/dashboard.sh harness  -> harness test slice (48 rows)  -> eval/results/harness.jsonl
set -euo pipefail
cd "$(dirname "$0")/.."

case "${1:-dev}" in
  dev)     RES=eval/results/dev.jsonl;     DATA=datasets/v2/business-prompts-v2.jsonl ;;
  test)    RES=eval/results/test.jsonl;    DATA=datasets/v2/business-prompts-v2.jsonl ;;
  harness) RES=eval/results/harness.jsonl; DATA=datasets/v2/all-prompts-v2.jsonl ;;
  *) echo "usage: $0 [dev|test|harness]" >&2; exit 1 ;;
esac

echo "dashboard -> $RES  (data: $DATA)"
exec .venv/bin/python eval/dashboard_server.py --data "$DATA" --results "$RES" --open
