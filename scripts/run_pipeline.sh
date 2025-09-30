#!/usr/bin/env bash
# scripts/run_pipeline.sh
# Hybrid venv selection: prefer root/.venv, fallback to component .venv, then system python.
# Usage: ./scripts/run_pipeline.sh [--nlp-tz path] [--ifc path] [--out path] [--host host] [--port port]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NLPCLI="$REPO_ROOT/nlp_core/nlp_core/run_cli.py"
BIMCLI="$REPO_ROOT/bim_core/bim_core/run_cli.py"
SENDCLI="$REPO_ROOT/scripts/send_stubs_cli.py"

NLPTZ=""
IFC_PATH=""
BIM_OUT="$REPO_ROOT/bim_core/runs"
HOST="127.0.0.1"
PORT="9090"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --nlp-tz) NLPTZ="$2"; shift 2;;
    --ifc) IFC_PATH="$2"; shift 2;;
    --out) BIM_OUT="$2"; shift 2;;
    --host) HOST="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 1;;
  esac
done

echo "Pipeline params:"
echo " NLP TZ: ${NLPTZ:-(auto)}"
echo " IFC: ${IFC_PATH:-(auto)}"
echo " BIM out: $BIM_OUT"
echo " MCP host: $HOST:$PORT"
echo

# Hybrid python chooser: prefer root .venv, fallback to component .venv, else system python
choose_python() {
  comp_dir="$1"  # component dir or empty
  # 1) root venv
  if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    echo "$REPO_ROOT/.venv/bin/python"
    return
  elif [ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]; then
    echo "$REPO_ROOT/.venv/Scripts/python.exe"
    return
  fi
  # 2) component venv
  if [ -n "$comp_dir" ]; then
    if [ -x "$comp_dir/.venv/bin/python" ]; then
      echo "$comp_dir/.venv/bin/python"; return
    elif [ -x "$comp_dir/.venv/Scripts/python.exe" ]; then
      echo "$comp_dir/.venv/Scripts/python.exe"; return
    fi
  fi
  # 3) fallback
  echo "python"
}

# Step 1: NLP
echo "=== Step 1/4: NLP ==="
NLPPY=$(choose_python "$REPO_ROOT/nlp_core")
if [ -z "$NLPTZ" ]; then
  NLPTZ="$REPO_ROOT/nlp_core/input/TZ_object.docx"
fi
"$NLPPY" "$NLPCLI" --tz "$NLPTZ" --out "$REPO_ROOT/nlp_core/OUT/result.json" -v
if [ ! -f "$REPO_ROOT/nlp_core/OUT/result.json" ]; then
  echo "ERROR: NLP output not found"
  exit 11
fi
echo "NLP ok."

# Step 2: BIM
echo
echo "=== Step 2/4: BIM ==="
BIMPY=$(choose_python "$REPO_ROOT/bim_core")
BIM_ARGS=(--tz "$REPO_ROOT/nlp_core/OUT/result.json" --out "$BIM_OUT")
if [ -n "$IFC_PATH" ]; then BIM_ARGS+=(--ifc "$IFC_PATH"); fi
"$BIMPY" "$BIMCLI" "${BIM_ARGS[@]}" -v
STUBS="$BIM_OUT/stubs.json"
if [ ! -f "$STUBS" ]; then
  echo "ERROR: BIM did not produce stubs.json at $STUBS"
  exit 21
fi
echo "BIM ok, stubs produced: $STUBS"

# Step 3: check MCP
echo
echo "=== Step 3/4: Check MCP $HOST:$PORT ==="
check_tcp() {
  # try /dev/tcp approach
  if bash -c "cat < /dev/null > /dev/tcp/$HOST/$PORT" 2>/dev/null; then
    return 0
  else
    return 1
  fi
}
if check_tcp; then
  echo "MCP reachable"
else
  echo "MCP not reachable at $HOST:$PORT"
  echo "Please start MCP in FreeCAD (open FreeCAD -> Python Console) and run:"
  echo "  exec(open(r'$REPO_ROOT/mcp_server/mcp_serverV3.py', encoding='utf-8').read())"
  read -p "Press Enter when MCP server is up (or Ctrl+C to abort)..."
  if ! check_tcp; then
    echo "ERROR: MCP still not reachable"
    exit 30
  fi
fi

# Step 4: send stubs
echo
echo "=== Step 4/4: Send stubs ==="
# choose system python for client (stdlib only) - but honor root venv if present
CLIENTPY=$(choose_python "")
"$CLIENTPY" "$SENDCLI" --stubs "$STUBS" --host "$HOST" --port "$PORT" -v
echo "Pipeline finished. Check FreeCAD for placed objects."
