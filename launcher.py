from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Callable

Command = Callable[[], int | None]

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))


COMMANDS: dict[str, tuple[str, str, str]] = {
    "gui": ("saftao.gui", "main", "Interface gráfica unificada"),
    "validate": ("scripts.validator_saft_ao", "main", "Validação estrita do SAF-T"),
    "autofix-soft": (
        "scripts.saft_ao_autofix_soft",
        "main",
        "Correções automáticas conservadoras",
    ),
    "autofix-hard": (
        "scripts.saft_ao_autofix_hard",
        "main",
        "Correções automáticas agressivas",
    ),
}


def _read_requirements(requirements_path: Path) -> list[str]:
    """Return the requirement specifiers defined in *requirements_path*."""

    requirements: list[str] = []
    if not requirements_path.is_file():
        return requirements

    for raw_line in requirements_path.read_text(encoding="utf-8").splitlines():
        requirement = raw_line.split("#", 1)[0].strip()
        if requirement:
            requirements.append(requirement)
    return requirements


def _install_requirements(
    requirements_path: Path, *, reason: str | None = None
) -> None:
    """Trigger ``pip install`` for the provided requirements file."""

    message = "Dependências desatualizadas ou em falta detectadas."
    if reason:
        message += f" Dependência '{reason}' em falta."
    print(
        message + " A executar 'pip install -r requirements.txt'.",
        file=sys.stderr,
    )

    command = [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)]
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise SystemExit(
            "Falha ao instalar dependências obrigatórias. "
            "Execute manualmente: pip install -r requirements.txt",
        )


def _ensure_packaging(
    requirements_path: Path,
) -> tuple[Callable[[], dict[str, str]], Callable[[str], Any]]:
    """Guarantee that the ``packaging`` module is importable."""

    try:
        from packaging.markers import default_environment
        from packaging.requirements import Requirement
    except ModuleNotFoundError as exc:
        if exc.name != "packaging":
            raise

        _install_requirements(requirements_path, reason="packaging")

        try:
            from packaging.markers import default_environment
            from packaging.requirements import Requirement
        except ModuleNotFoundError as retry_exc:  # pragma: no cover - defensive
            raise SystemExit(
                "A dependência 'packaging' continua em falta após tentativa de instalação."
            ) from retry_exc

    return default_environment, Requirement


def _missing_requirements(
    requirements: list[str],
    *,
    requirement_factory: Callable[[str], Any],
    environment_factory: Callable[[], dict[str, str]],
) -> list[str]:
    """Return the requirements that are not satisfied in the environment."""

    if not requirements:
        return []

    environment = environment_factory()
    missing: list[str] = []

    for raw_spec in requirements:
        requirement = requirement_factory(raw_spec)

        marker = getattr(requirement, "marker", None)
        if marker and not marker.evaluate(environment):
            continue

        try:
            installed_version = importlib_metadata.version(requirement.name)
        except importlib_metadata.PackageNotFoundError:
            missing.append(raw_spec)
            continue

        specifier = getattr(requirement, "specifier", None)
        if specifier and not specifier.contains(
            installed_version,
            prereleases=True,
        ):
            missing.append(raw_spec)

    return missing


def ensure_requirements(requirements_path: Path | None = None) -> None:
    """Ensure that dependencies listed in ``requirements.txt`` are satisfied."""

    if requirements_path is None:
        requirements_path = PROJECT_ROOT / "requirements.txt"

    requirements = _read_requirements(requirements_path)
    environment_factory, requirement_factory = _ensure_packaging(requirements_path)
    missing = _missing_requirements(
        requirements,
        requirement_factory=requirement_factory,
        environment_factory=environment_factory,
    )
    if not missing:
        return

    _install_requirements(requirements_path)

    # Confirm that the installation resolved the missing requirements.
    environment_factory, requirement_factory = _ensure_packaging(requirements_path)
    still_missing = _missing_requirements(
        requirements,
        requirement_factory=requirement_factory,
        environment_factory=environment_factory,
    )
    if still_missing:
        raise SystemExit(
            "Algumas dependências continuam em falta: " + ", ".join(still_missing)
        )


def _load_command(name: str) -> Command:
    module_name, func_name, _ = COMMANDS[name]
    module = importlib.import_module(module_name)
    command = getattr(module, func_name)
    return command  # type: ignore[return-value]


def _run_command(name: str, args: list[str]) -> int:
    command = _load_command(name)
    old_argv = sys.argv[:]
    sys.argv = [f"{name}.py", *args]
    try:
        result = command()
    except SystemExit as exc:  # pragma: no cover - delegate exit handling
        code = exc.code if isinstance(exc.code, int) else 0
        return code
    finally:
        sys.argv = old_argv
    if isinstance(result, int):
        return result
    return 0


def main(argv: list[str] | None = None) -> int:
    ensure_requirements()

    parser = argparse.ArgumentParser(
        description="Ponto único de entrada para as ferramentas SAF-T (AO)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_commands",
        help="Apresenta a lista de comandos disponíveis e termina",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=COMMANDS.keys(),
        help="Ferramenta a executar (omitir para abrir a interface gráfica)",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help="Argumentos adicionais passados ao comando seleccionado",
    )

    ns = parser.parse_args(argv)

    if ns.list_commands:
        for key, (_, _, description) in COMMANDS.items():
            print(f"{key:14s} - {description}")
        return 0

    if ns.command is None:
        if ns.args:
            parser.error("é necessário indicar um comando antes dos argumentos")
        command = "gui"
    else:
        command = ns.command

    return _run_command(command, ns.args)


if __name__ == "__main__":
    sys.exit(main())
