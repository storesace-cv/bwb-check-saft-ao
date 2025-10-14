#!/usr/bin/env python3
"""
Launcher do GUI com verificação de requirements antes do arranque.

Funcionalidades:
- Se existir requirements.txt, calcula um hash e compara com um carimbo guardado
  (.venv/.req_hash ou ./.req_hash). Se mudou (ou não houver carimbo), instala/atualiza
  dependências via pip e atualiza o carimbo.
- Garante que PySide6 está disponível antes de arrancar o GUI.
- Permite forçar reinstalação com FORCE_PIP_INSTALL=1
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
REQ_FILE = PROJECT_ROOT / "requirements.txt"

# Onde guardar o carimbo do hash (prioriza .venv/.req_hash se existir .venv)
VENV_DIR = PROJECT_ROOT / ".venv"
REQ_STAMP = (VENV_DIR / ".req_hash") if VENV_DIR.exists() else (PROJECT_ROOT / ".req_hash")

# Opcionais via ambiente
FORCE_PIP_INSTALL = os.getenv("FORCE_PIP_INSTALL", "").strip() in {"1", "true", "yes", "on"}
PIP_EXTRA_ARGS = os.getenv("PIP_EXTRA_ARGS", "").strip()  # ex: "--no-cache-dir"


def _print(msg: str) -> None:
    print(msg, flush=True)


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_stamp(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None


def _write_stamp(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n", encoding="utf-8")


def _ensure_requirements_installed() -> None:
    """Se existir requirements.txt, instala/atualiza quando necessário."""
    if not REQ_FILE.exists():
        _print("➡️  Sem requirements.txt — a arrancar sem validação de dependências.")
        return

    req_hash = _hash_file(REQ_FILE)
    old_hash = _read_stamp(REQ_STAMP)

    if FORCE_PIP_INSTALL or (old_hash != req_hash):
        if FORCE_PIP_INSTALL:
            _print("♻️  FORCE_PIP_INSTALL=1 → reinstalação forçada de dependências…")
        else:
            _print("🔍 Alteração detetada em requirements.txt → a instalar/atualizar dependências…")

        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--upgrade",
            "-r",
            str(REQ_FILE),
        ]
        if PIP_EXTRA_ARGS:
            cmd.extend(PIP_EXTRA_ARGS.split())

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            _print("❌ Falha ao instalar dependências de requirements.txt.")
            _print(f"   Comando: {' '.join(cmd)}")
            _print(f"   Código de saída: {e.returncode}")
            raise SystemExit(1)

        _write_stamp(REQ_STAMP, req_hash)
        _print("✅ Dependências OK.")
    else:
        _print("✅ Dependências já em conformidade (sem alterações).")


def _ensure_qt_is_installed() -> None:
    """Garante PySide6 antes de importar o app."""
    if importlib.util.find_spec("PySide6") is not None:
        return
    _print(
        "❌ PySide6 não encontrado.\n"
        "   Instala as dependências com:  pip install -r requirements.txt\n"
        "   (ou define FORCE_PIP_INSTALL=1 para forçar instalação no arranque)"
    )
    raise SystemExit(1)


def main() -> None:
    # 1) Dependências
    _ensure_requirements_installed()

    # 2) PySide6
    _ensure_qt_is_installed()

    # 3) Import tardio do teu app (evita falhas antes de deps estarem OK)
    try:
        from app.ui.app import main as app_main  # ajusta o import se necessário
    except Exception as exc:
        _print(f"❌ Erro a importar a aplicação: {exc}")
        raise

    # 4) Arrancar GUI
    app_main()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        raise
    except Exception as e:
        _print(f"💥 Erro inesperado: {e}")
        raise
