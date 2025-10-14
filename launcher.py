#!/usr/bin/env python3
"""
Launcher do GUI com verificação de requirements antes do arranque.

Funcionalidades:
- Se existir requirements.txt, calcula um hash e compara com um carimbo guardado
  (.venv/.req_hash ou ./.req_hash). Se mudou (ou não houver carimbo), instala/atualiza
  dependências via pip e atualiza o carimbo.
- Permite forçar reinstalação com FORCE_PIP_INSTALL=1
"""

from __future__ import annotations

import hashlib
import importlib.util
import importlib.metadata as importlib_metadata
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

from packaging.markers import default_environment
from packaging.requirements import Requirement


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


def ensure_requirements(req_file: Path) -> None:
    """Garantir que os requisitos listados estão instalados."""

    if not req_file.exists():
        return

    raw_lines = req_file.read_text(encoding="utf-8").splitlines()
    requirements = [
        line.strip()
        for line in raw_lines
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not requirements:
        return

    missing = _missing_requirements(
        requirements,
        requirement_factory=Requirement,
        environment_factory=default_environment,
    )
    if missing:
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        result = subprocess.run(cmd, check=False)
        if getattr(result, "returncode", 0) != 0:
            raise SystemExit(result.returncode)


def _missing_requirements(
    requirements: list[str],
    *,
    requirement_factory: Callable[[str], Requirement],
    environment_factory: Callable[[], dict[str, str]],
) -> list[str]:
    """Return a list of requirement strings that are not satisfied."""

    missing: list[str] = []
    environment = environment_factory()
    for requirement_text in requirements:
        try:
            requirement = requirement_factory(requirement_text)
        except Exception:  # pragma: no cover - requisitos inválidos
            missing.append(requirement_text)
            continue

        if requirement.marker and not requirement.marker.evaluate(environment):
            continue

        try:
            installed_version = importlib_metadata.version(requirement.name)
        except importlib_metadata.PackageNotFoundError:
            missing.append(requirement_text)
            continue

        if requirement.specifier and installed_version not in requirement.specifier:
            missing.append(requirement_text)

    return missing


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

    ensure_requirements(REQ_FILE)


def _ensure_project_on_path() -> None:
    """Garante que o pacote ``saftao`` está disponível para importação."""

    if importlib.util.find_spec("saftao") is not None:
        return

    src_dir = PROJECT_ROOT / "src"
    if src_dir.exists():
        sys.path.insert(0, str(src_dir))

    if importlib.util.find_spec("saftao") is not None:
        return

    raise ModuleNotFoundError(
        "Não foi possível localizar o pacote 'saftao'. "
        "Certifica-te de que o projecto foi instalado (pip install -e .) "
        "ou que a pasta 'src' está presente."
    )


def main() -> None:
    # 1) Dependências
    _ensure_requirements_installed()

    # 2) Garantir que o pacote do projecto está acessível
    try:
        _ensure_project_on_path()
    except Exception as exc:
        _print(f"❌ Erro a preparar o ambiente da aplicação: {exc}")
        raise

    # 3) Import tardio do teu app (evita falhas antes de deps estarem OK)
    try:
        from saftao.gui import main as app_main
    except Exception as exc:
        _print(f"❌ Erro a importar a aplicação: {exc}")
        raise

    # 4) Arrancar GUI
    result = app_main()
    if isinstance(result, int):
        raise SystemExit(result)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        raise
    except Exception as e:
        _print(f"💥 Erro inesperado: {e}")
        raise
