from __future__ import annotations

import sys
import types

import pytest

import launcher


def _install_fake_pkg_resources(monkeypatch, require):
    fake_pkg = types.SimpleNamespace()
    fake_pkg.require = require
    fake_pkg.DistributionNotFound = type(
        "DistributionNotFound", (Exception,), {}
    )
    fake_pkg.VersionConflict = type("VersionConflict", (Exception,), {})
    monkeypatch.setitem(sys.modules, "pkg_resources", fake_pkg)
    return fake_pkg


def test_ensure_requirements_no_missing(tmp_path, monkeypatch):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("foo==1.0\n", encoding="utf-8")

    calls: list[str] = []

    def fake_require(requirement: str):
        calls.append(requirement)
        return []

    _install_fake_pkg_resources(monkeypatch, fake_require)
    run_calls: list[list[str]] = []

    def fake_run(cmd, check):
        run_calls.append(cmd)
        raise AssertionError("pip should not be executed when requirements match")

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    launcher.ensure_requirements(req_file)

    assert calls == ["foo==1.0"]
    assert not run_calls


def test_ensure_requirements_installs_missing(tmp_path, monkeypatch):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("foo==1.0\n", encoding="utf-8")

    install_triggered = False

    def fake_require(requirement: str):
        if not install_triggered:
            raise sys.modules["pkg_resources"].DistributionNotFound("missing")
        return []

    fake_pkg = _install_fake_pkg_resources(monkeypatch, fake_require)

    executed_commands: list[list[str]] = []

    def fake_run(cmd, check):
        nonlocal install_triggered
        executed_commands.append(cmd)
        install_triggered = True
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    launcher.ensure_requirements(req_file)

    assert executed_commands == [[sys.executable, "-m", "pip", "install", "-r", str(req_file)]]

    # After installation, the requirement should be checked again successfully.
    assert fake_pkg.require("foo==1.0") == []


def test_ensure_requirements_install_failure(tmp_path, monkeypatch):
    req_file = tmp_path / "requirements.txt"
    req_file.write_text("foo==1.0\n", encoding="utf-8")

    def fake_require(_requirement: str):
        raise sys.modules["pkg_resources"].DistributionNotFound("missing")

    _install_fake_pkg_resources(monkeypatch, fake_require)

    def fake_run(cmd, check):
        return types.SimpleNamespace(returncode=1)

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    with pytest.raises(SystemExit):
        launcher.ensure_requirements(req_file)
