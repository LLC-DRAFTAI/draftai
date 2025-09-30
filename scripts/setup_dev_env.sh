#!/usr/bin/env bash
# scripts/setup_dev_env.sh
# Создаёт root .venv (в корне репо) и component .venv при необходимости.
# Устанавливает зависимости: prefer root .venv -> иначе component .venv.
# Usage: ./scripts/setup_dev_env.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Repository root: $REPO_ROOT"

# Опции: можно задать PYTHON_CMD=python3 для нестандартных систем
PYTHON_CMD=${PYTHON_CMD:-python3}

# Create root venv and install main requirements (from nlp_core)
create_root_venv() {
  ROOT_VENV="$REPO_ROOT/.venv"
  if [ -d "$ROOT_VENV" ]; then
    echo "Root venv already exists at $ROOT_VENV"
  else
    echo "Creating root venv at $ROOT_VENV"
    "$PYTHON_CMD" -m venv "$ROOT_VENV"
    PIP="$ROOT_VENV/bin/pip"
    echo "Upgrading pip in root venv..."
    "$PIP" install --upgrade pip
    if [ -f "$REPO_ROOT/nlp_core/requirements.txt" ]; then
      echo "Installing nlp_core requirements into root venv..."
      "$PIP" install -r "$REPO_ROOT/nlp_core/requirements.txt"
    else
      echo "No nlp_core/requirements.txt found — root venv created but no packages installed."
    fi
  fi
}

create_component_venv_if_needed() {
  comp_dir="$1"
  req="$comp_dir/requirements.txt"
  venv_dir="$comp_dir/.venv"
  if [ -f "$req" ]; then
    if [ -d "$venv_dir" ]; then
      echo "Component venv already exists: $venv_dir"
    else
      echo "Creating component venv for $comp_dir at $venv_dir"
      "$PYTHON_CMD" -m venv "$venv_dir"
      if [ -x "$venv_dir/bin/pip" ]; then
        pip_exec="$venv_dir/bin/pip"
      else
        pip_exec="$venv_dir/Scripts/pip"
      fi
      echo "Installing requirements for $comp_dir"
      "$pip_exec" install --upgrade pip
      "$pip_exec" install -r "$req"
    fi
  else
    echo "No requirements for component $comp_dir (skipping creating component venv)."
  fi
}

echo "=== Creating root venv (preferred) ==="
create_root_venv

echo
echo "=== Optionally create per-component venvs if they have requirements ==="
create_component_venv_if_needed "$REPO_ROOT/nlp_core"
create_component_venv_if_needed "$REPO_ROOT/bim_core"

echo
echo "NOTE: MCP server requires FreeCAD and is NOT installed via pip. Install FreeCAD manually."
echo "If you plan to run MCP via system python, set FREECAD_PATH environment variable."
echo "Setup complete."
