from pathlib import Path

from setuptools import setup

APP = ["scripts/validator_saft_ao.py"]
NAME = "Verificador SAFT-AO"
IDENTIFIER = "ao.bwb.verificador-saft"

SCHEMA_DIR = Path("schemas")
RESOURCES = [str(SCHEMA_DIR)] if SCHEMA_DIR.exists() else []

ICON_FILE = Path("src/saftao/bwb-saft-app.png")
if ICON_FILE.exists():
    RESOURCES.append(str(ICON_FILE))

OPTIONS = {
    "argv_emulation": True,
    "packages": ["saftao", "saftao._compat"],
    "resources": RESOURCES,
    "plist": {
        "CFBundleName": NAME,
        "CFBundleDisplayName": NAME,
        "CFBundleIdentifier": IDENTIFIER,
    },
}


def _extend_with_pyside6() -> None:
    """Include PySide6 frameworks/plugins when available.

    The ``py2app`` bootstrap executed on GitHub's macOS runners may miss the
    Qt frameworks and the ``platforms`` plugin directory, causing the produced
    ``.app`` bundle to crash with the classic ``Launch error`` message.

    To make the bundle self-contained we explicitly add the PySide6 package,
    the Qt frameworks and the plugin directory that ships the ``libqcocoa``
    backend required on macOS.
    """

    try:
        import PySide6  # type: ignore
    except ModuleNotFoundError:
        return

    if "PySide6" not in OPTIONS["packages"]:
        OPTIONS["packages"].append("PySide6")

    pyside6_dir = Path(PySide6.__file__).resolve().parent
    qt_dir = pyside6_dir / "Qt"

    plugin_dir = qt_dir / "plugins"
    if plugin_dir.is_dir():
        OPTIONS.setdefault("resources", []).append(str(plugin_dir))

    frameworks_dir = qt_dir / "lib"
    frameworks: list[str] = []
    if frameworks_dir.is_dir():
        for framework in sorted(frameworks_dir.glob("Qt*.framework")):
            if framework.is_dir():
                binary = framework / framework.stem
                if binary.exists():
                    frameworks.append(str(binary))

        for dylib in sorted(frameworks_dir.glob("*.dylib")):
            if dylib.is_file():
                frameworks.append(str(dylib))

    if frameworks:
        OPTIONS.setdefault("frameworks", []).extend(frameworks)


# Ensure the compatibility shims are always bundled so the application can
# provide deprecated stdlib modules (e.g. ``imp``) that third-party
# dependencies might still import on newer Python releases.
OPTIONS.setdefault("includes", []).append("saftao._compat.imp")


_extend_with_pyside6()

setup(
    name=NAME,
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
