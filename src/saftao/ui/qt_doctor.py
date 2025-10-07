"""Ferramenta de diagnóstico para o ambiente Qt/PySide6.

O objectivo deste utilitário é facilitar a identificação dos problemas
clássicos relacionados com o carregamento dos plugins do Qt em macOS,
especialmente o plugin ``cocoa`` necessário para criar janelas.

O comando inspecta as variáveis de ambiente relevantes, confirma se os
plugins existem dentro da instalação activa de PySide6 e sugere um
procedimento de recuperação caso o plugin ``libqcocoa.dylib`` não esteja
disponível.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from textwrap import dedent

LOGGER_PREFIX = "[qt-doctor]"


def _print(message: str) -> None:
    sys.stdout.write(f"{LOGGER_PREFIX} {message}\n")


def _gather_environment() -> dict[str, str]:
    relevant = {
        "QT_PLUGIN_PATH": os.environ.get("QT_PLUGIN_PATH", "<não definido>"),
        "QT_QPA_PLATFORM_PLUGIN_PATH": os.environ.get(
            "QT_QPA_PLATFORM_PLUGIN_PATH", "<não definido>"
        ),
        "DYLD_LIBRARY_PATH": os.environ.get("DYLD_LIBRARY_PATH", "<não definido>"),
        "DYLD_FRAMEWORK_PATH": os.environ.get(
            "DYLD_FRAMEWORK_PATH", "<não definido>"
        ),
    }
    return relevant


def _describe_environment(env: dict[str, str]) -> None:
    _print("Variáveis de ambiente relevantes:")
    for key, value in env.items():
        if value == "<não definido>":
            _print(f"  - {key}: {value}")
        else:
            chunks = value.split(os.pathsep)
            if len(chunks) == 1:
                _print(f"  - {key}: {value}")
            else:
                _print(f"  - {key}:")
                for chunk in chunks:
                    _print(f"      • {chunk or '<vazio>'}")


def _discover_pyside6_paths() -> tuple[Path, Path] | None:
    spec = importlib.util.find_spec("PySide6")
    if spec is None or not spec.submodule_search_locations:
        _print(
            "PySide6 não está instalado ou não foi localizado na virtualenv actual."
        )
        return None

    PySide6 = importlib.import_module("PySide6")
    package_path = Path(PySide6.__file__).resolve()
    plugin_root = package_path.with_name("Qt") / "plugins"
    platform_dir = plugin_root / "platforms"
    return plugin_root, platform_dir


def _check_cocoa_plugin(platform_dir: Path) -> bool:
    cocoa = platform_dir / "libqcocoa.dylib"
    if cocoa.exists():
        _print(f"Plugin 'libqcocoa.dylib' encontrado: {cocoa}")
        return True
    _print(
        "Plugin 'libqcocoa.dylib' não encontrado. O Qt não conseguirá inicializar o backend Cocoa."
    )
    return False


def _suggest_remediation(platform_dir: Path) -> None:
    instructions = dedent(
        f"""
        Passos recomendados para recuperar o ambiente no macOS:

          1. Limpe variáveis que possam apontar para instalações Qt desactualizadas::
               unset QT_PLUGIN_PATH
               unset QT_QPA_PLATFORM_PLUGIN_PATH

          2. Reinstale PySide6 e shiboken6 dentro da virtualenv activa::
               pip uninstall -y PySide6 shiboken6
               pip install --no-cache --force-reinstall "PySide6==6.7.*" "shiboken6==6.7.*"

          3. Confirme se o plugin Cocoa existe::
               python - <<'PY'
               import pathlib, PySide6
               p = pathlib.Path(PySide6.__file__).with_name("Qt") / "plugins" / "platforms"
               print("Platforms dir:", p)
               print("Has cocoa:", (p / "libqcocoa.dylib").exists())
               PY

          4. Exporte explicitamente o directório de plataformas para testar::
               export QT_QPA_PLATFORM_PLUGIN_PATH="{platform_dir}"
               python3 launcher.py
        """
    ).strip()
    for line in instructions.splitlines():
        _print(line)


def run_diagnostics() -> int:
    _print("Iniciar diagnóstico do ambiente Qt/PySide6…")
    env = _gather_environment()
    _describe_environment(env)

    discovered = _discover_pyside6_paths()
    if not discovered:
        return 1

    plugin_root, platform_dir = discovered
    _print(f"Directório de plugins do PySide6: {plugin_root}")
    _print(f"Directório de plataformas: {platform_dir}")

    if not platform_dir.exists():
        _print(
            "O directório de plataformas não existe. Reinstale PySide6 conforme os passos recomendados."
        )
        _suggest_remediation(platform_dir)
        return 2

    cocoa_ok = _check_cocoa_plugin(platform_dir)
    if not cocoa_ok:
        _suggest_remediation(platform_dir)
        return 3

    _print(
        "Ambiente Cocoa detectado correctamente. Caso o arranque continue a falhar, utilize o valor acima em QT_QPA_PLATFORM_PLUGIN_PATH."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m saftao.ui.qt_doctor",
        description="Diagnostica problemas comuns do Qt no macOS",
    )
    parser.add_argument(
        "--no-env", action="store_true", help="Não listar as variáveis de ambiente."
    )
    args = parser.parse_args(argv)

    if args.no_env:
        plugin_info = _discover_pyside6_paths()
        if not plugin_info:
            return 1
        _, platform_dir = plugin_info
        cocoa_ok = _check_cocoa_plugin(platform_dir)
        if not cocoa_ok:
            _suggest_remediation(platform_dir)
            return 3
        return 0

    return run_diagnostics()


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
