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


# Ensure the compatibility shims are always bundled so the application can
# provide deprecated stdlib modules (e.g. ``imp``) that third-party
# dependencies might still import on newer Python releases.
OPTIONS.setdefault("includes", []).append("saftao._compat.imp")

setup(
    name=NAME,
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
