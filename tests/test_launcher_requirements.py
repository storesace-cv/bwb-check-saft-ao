from __future__ import annotations

import sys
import types

import pytest

pytest.importorskip("packaging")
from packaging.markers import default_environment
from packaging.requirements import Requirement

def test_ensure_requirements_no_missing(tmp_path, monkeypatch):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("foo==1.0\n", encoding="utf-8")

    calls: list[list[str]] = []

    #    -------- adicionado pelo Codex a 2025-10-07T10:37:03Z  --------
    def fake_missing(requirements: list[str]) -> list[str]:
        calls.append(requirements)
        return []

    monkeypatch.setattr(launcher, "_missing_requirements", fake_missing)
    run_calls: list[list[str]] = []

    def fake_run(cmd, check):
        run_calls.append(cmd)
        raise AssertionError("pip should not be executed when requirements match")

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    launcher.ensure_requirements(req_file)

    assert calls == [["foo==1.0"]]
    assert not run_calls


def test_ensure_requirements_installs_missing(tmp_path, monkeypatch):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("foo==1.0\n", encoding="utf-8")

    install_triggered = False

    #    -------- adicionado pelo Codex a 2025-10-07T10:37:03Z  --------
    def fake_missing(requirements: list[str]) -> list[str]:
        nonlocal install_triggered
        if install_triggered:
            return []
        return ["foo==1.0"]

    monkeypatch.setattr(launcher, "_missing_requirements", fake_missing)

    executed_commands: list[list[str]] = []

    def fake_run(cmd, check):
        nonlocal install_triggered
        executed_commands.append(cmd)
        install_triggered = True
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    launcher.ensure_requirements(req_file)

    assert executed_commands == [[sys.executable, "-m", "pip", "install", "-r", str(req_file)]]


def test_ensure_requirements_install_failure(tmp_path, monkeypatch):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("foo==1.0\n", encoding="utf-8")

    #    -------- adicionado pelo Codex a 2025-10-07T10:37:03Z  --------
    def fake_missing(requirements: list[str]) -> list[str]:
        return ["foo==1.0"]

    monkeypatch.setattr(launcher, "_missing_requirements", fake_missing)

    def fake_run(cmd, check):
        return types.SimpleNamespace(returncode=1)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        launcher.ensure_requirements(req_file)


#    -------- adicionado pelo Codex a 2025-10-07T10:37:03Z  --------
def test_missing_requirements_detects_absent_package(monkeypatch):
    def fake_version(_name: str) -> str:
        raise launcher.importlib_metadata.PackageNotFoundError

    monkeypatch.setattr(launcher.importlib_metadata, "version", fake_version)

    missing = launcher._missing_requirements(["foo==1.0"])

    assert missing == ["foo==1.0"]


#    -------- adicionado pelo Codex a 2025-10-07T10:37:03Z  --------
def test_missing_requirements_accepts_matching_version(monkeypatch):
    def fake_version(_name: str) -> str:
        return "1.0"

    monkeypatch.setattr(launcher.importlib_metadata, "version", fake_version)

    missing = launcher._missing_requirements(["foo==1.0"])

    assert missing == []
