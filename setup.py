from pathlib import Path

from setuptools import setup

APP = ["scripts/validator_saft_ao.py"]
NAME = "Verificador SAFT-AO"
IDENTIFIER = "ao.bwb.verificador-saft"

SCHEMA_DIR = Path("schemas")
RESOURCES = [str(SCHEMA_DIR)] if SCHEMA_DIR.exists() else []

ICON_FILE = Path("src/saftao/bwb-saft-app.svg")
if ICON_FILE.exists():
    RESOURCES.append(str(ICON_FILE))

OPTIONS = {
    "argv_emulation": True,
    "packages": ["saftao"],
    "resources": RESOURCES,
    "plist": {
        "CFBundleName": NAME,
        "CFBundleDisplayName": NAME,
        "CFBundleIdentifier": IDENTIFIER,
    },
}

setup(
    name=NAME,
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
