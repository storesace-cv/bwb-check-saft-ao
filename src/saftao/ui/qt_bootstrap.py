"""Configuração antecipada do ambiente Qt para a aplicação SAF-T (AO).

Este módulo replica o comportamento do bootstrap utilizado no projecto
BWB Fichas Técnicas Vínicas, garantindo que as variáveis de ambiente
relacionadas com plugins Qt são definidas antes da criação do
``QApplication``. O código é adaptado para PySide6 mas mantém a lógica
de detecção dinâmica dos directórios de plugins descrita no guia de
implementação do *splash screen* transparente.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from typing import Iterable

__all__ = [
    "apply_plugin_environment",
    "preconfigure_plugin_environment",
]

LOGGER = logging.getLogger("saftao.ui.qt_bootstrap")

_PLUGIN_SUFFIXES = {".dll", ".dylib", ".so"}

_DISCOVERED_PLUGIN_PATHS: tuple[Path, Path] | None = None


def _iter_plugin_roots(include_qt_library_info: bool) -> Iterable[Path]:
    """Yield candidate directories that might contain Qt plugins."""

    seen: set[Path] = set()

    for env_name in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
        raw_value = os.environ.get(env_name)
        if not raw_value:
            continue
        for chunk in raw_value.split(os.pathsep):
            if not chunk:
                continue
            path = Path(chunk).expanduser().resolve()
            if path in seen:
                continue
            seen.add(path)
            if (
                env_name == "QT_QPA_PLATFORM_PLUGIN_PATH"
                and path.name == "platforms"
            ):
                yield path.parent
            else:
                yield path

    spec = importlib.util.find_spec("PySide6")
    if spec and spec.submodule_search_locations:
        pyside_root = Path(spec.submodule_search_locations[0]).resolve()
        if pyside_root not in seen:
            seen.add(pyside_root)
            yield pyside_root
        for relative in (Path("Qt/plugins"), Path("plugins")):
            candidate = (pyside_root / relative).resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            yield candidate

    if include_qt_library_info:
        try:
            from PySide6.QtCore import QLibraryInfo
        except ImportError:
            LOGGER.debug("PySide6 ainda não disponível para QLibraryInfo.")
        else:
            qt_plugins = Path(
                QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
            ).resolve()
            if qt_plugins not in seen:
                seen.add(qt_plugins)
                yield qt_plugins


def _contains_platform_plugins(directory: Path) -> bool:
    if not directory.is_dir():
        return False

    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        suffix = entry.suffix.lower()
        if suffix not in _PLUGIN_SUFFIXES:
            continue
        stem = entry.stem.lower()
        if stem.startswith("q") or stem.startswith("libq"):
            return True
    return False


def _discover_platform_plugin_dirs(
    include_qt_library_info: bool,
) -> tuple[Path, Path] | None:
    """Return ``(plugin_root, platform_dir)`` if any candidate contains Qt plugins."""

    for candidate in _iter_plugin_roots(include_qt_library_info):
        platform_dir = candidate / "platforms"
        if _contains_platform_plugins(platform_dir):
            return candidate, platform_dir

        if candidate.name == "platforms" and _contains_platform_plugins(candidate):
            return candidate.parent, candidate

    return None


def _set_qt_plugin_environment(plugin_root: Path, platform_dir: Path) -> None:
    os.environ["QT_PLUGIN_PATH"] = str(plugin_root)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platform_dir)
    LOGGER.info("QT_PLUGIN_PATH ajustado para %s", plugin_root)
    LOGGER.info("QT_QPA_PLATFORM_PLUGIN_PATH ajustado para %s", platform_dir)


def preconfigure_plugin_environment() -> None:
    """Discover Qt plugin paths before importing PySide6 widgets."""

    global _DISCOVERED_PLUGIN_PATHS

    if _DISCOVERED_PLUGIN_PATHS is not None:
        return

    discovered = _discover_platform_plugin_dirs(include_qt_library_info=False)
    if not discovered:
        LOGGER.debug(
            "Nenhum directório de plugins Qt detectado antes do import do PySide6."
        )
        return

    _DISCOVERED_PLUGIN_PATHS = discovered
    plugin_root, platform_dir = discovered
    LOGGER.debug(
        "Qt plugins detectados previamente em %s (plataformas: %s)",
        plugin_root,
        platform_dir,
    )
    _set_qt_plugin_environment(plugin_root, platform_dir)


def apply_plugin_environment() -> None:
    """Ensure PySide6 knows about the plugin directories after import."""

    global _DISCOVERED_PLUGIN_PATHS

    discovered = _DISCOVERED_PLUGIN_PATHS
    if discovered is None:
        discovered = _discover_platform_plugin_dirs(include_qt_library_info=True)
        if not discovered:
            LOGGER.warning("Não foi possível localizar plugins Qt adicionais.")
            return
        _DISCOVERED_PLUGIN_PATHS = discovered

    plugin_root, platform_dir = discovered
    _set_qt_plugin_environment(plugin_root, platform_dir)

    try:
        from PySide6.QtCore import QCoreApplication
    except ImportError:  # pragma: no cover - defensive
        LOGGER.warning(
            "PySide6 indisponível ao aplicar directórios de plugins; a ignorar."
        )
        return

    existing_paths = {Path(path) for path in QCoreApplication.libraryPaths()}
    for directory in (plugin_root, platform_dir):
        if directory not in existing_paths:
            QCoreApplication.addLibraryPath(str(directory))
            existing_paths.add(directory)
            LOGGER.debug("Adicionado %s às library paths do Qt", directory)


# O bootstrap deve ocorrer imediatamente aquando da importação.
preconfigure_plugin_environment()
