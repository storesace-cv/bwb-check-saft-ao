#!/usr/bin/env bash
set -euo pipefail

# --- Settings (override via env if needed) ---
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-requirements.txt}"

# --- Resolve project directory and move there ---
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "▶ Using Python: ${PYTHON_BIN}"
echo "▶ Project dir: ${PROJECT_DIR}"
echo "▶ Venv dir:    ${VENV_DIR}"
echo "▶ Requirements: ${REQUIREMENTS_FILE}"

# --- Create venv if it doesn't exist ---
if [[ ! -d "${VENV_DIR}" || ! -f "${VENV_DIR}/bin/activate" ]]; then
  echo "▶ Creating virtual environment..."
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# --- Activate venv ---
# shellcheck disable=SC1090
source "${VENV_DIR}/bin/activate"
echo "▶ Virtualenv activated: $(python -V)"

# --- Ensure pip is up-to-date ---
python -m pip install --upgrade pip wheel setuptools >/dev/null 2>&1 || true

# --- Install requirements if present ---
if [[ -f "${REQUIREMENTS_FILE}" ]]; then
  echo "▶ Checking/Installing requirements..."
  # This will install anything missing; already satisfied packages are skipped.
  pip install -r "${REQUIREMENTS_FILE}"
  # Optional sanity check for dependency conflicts (won't install anything)
  pip check || true
else
  echo "⚠ No requirements.txt found. Skipping dependency install."
fi

# --- Run the app ---
echo "▶ Starting: python launcher.py"
exec python launcher.py
