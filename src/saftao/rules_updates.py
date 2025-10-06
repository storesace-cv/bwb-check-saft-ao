"""Ferramentas para gerir actualizações de regras e esquemas SAF-T (AO).

Este módulo fornece um utilitário de linha de comandos simples que copia os
ficheiros de regras fornecidos para a directoria ``rules_updates/`` e actualiza
um índice em JSON com o respectivo metadado. A funcionalidade permite manter um
histórico auditável das alterações que chegam da AGT e serve como ponto único de
referência para outros desenvolvedores integrarem essas novidades no código.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = REPO_ROOT / "rules_updates"
SCHEMAS_DIR = REPO_ROOT / "schemas"
INDEX_PATH = RULES_DIR / "index.json"


@dataclass
class Artifact:
    """Representa um ficheiro copiado para a directoria de updates."""

    type: str
    name: str
    sha256: str
    relative_path: str


@dataclass
class RuleUpdate:
    """Entrada registada no índice de actualizações."""

    identifier: str
    note: str
    created_at: str
    tag: str | None
    folder: str
    artifacts: list[Artifact]


def slugify(value: str) -> str:
    """Gerar *slug* seguro para ser usado em nomes de pastas."""

    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower())
    normalized = normalized.strip("-")
    return normalized or "update"


def sha256sum(path: Path) -> str:
    """Calcular o hash SHA256 do ficheiro fornecido."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_artifact(source: Path, destination: Path, *, artifact_type: str) -> Artifact:
    """Copiar um ficheiro e devolver a representação do artefacto."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return Artifact(
        type=artifact_type,
        name=destination.name,
        sha256=sha256sum(destination),
        relative_path=str(destination.relative_to(REPO_ROOT)),
    )


def load_index() -> list[RuleUpdate]:
    """Ler o índice existente do disco."""

    if not INDEX_PATH.exists():
        return []

    with INDEX_PATH.open("r", encoding="utf-8") as handle:
        raw_entries = json.load(handle)

    entries: list[RuleUpdate] = []
    for entry in raw_entries:
        artifacts = [Artifact(**artifact) for artifact in entry["artifacts"]]
        entries.append(
            RuleUpdate(
                identifier=entry["identifier"],
                note=entry["note"],
                created_at=entry["created_at"],
                tag=entry.get("tag"),
                folder=entry["folder"],
                artifacts=artifacts,
            )
        )
    return entries


def save_index(entries: Iterable[RuleUpdate]) -> None:
    """Escrever o índice para disco com formatação estável."""

    serializable = []
    for entry in entries:
        serializable.append(
            {
                "identifier": entry.identifier,
                "note": entry.note,
                "created_at": entry.created_at,
                "tag": entry.tag,
                "folder": entry.folder,
                "artifacts": [asdict(artifact) for artifact in entry.artifacts],
            }
        )

    with INDEX_PATH.open("w", encoding="utf-8") as handle:
        json.dump(serializable, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def register_update(
    *,
    note: str,
    xsd: Path | None,
    rule_files: list[Path],
    tag: str | None,
    schema_target: str | None,
) -> RuleUpdate:
    """Registar uma nova actualização na directoria ``rules_updates``."""

    timestamp = datetime.now(timezone.utc)
    identifier = f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}-{slugify(note)}"

    update_dir = RULES_DIR / identifier
    update_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[Artifact] = []

    if xsd is not None:
        if not xsd.exists():
            msg = f"Ficheiro XSD '{xsd}' não encontrado"
            raise FileNotFoundError(msg)

        destination = update_dir / xsd.name
        artifacts.append(copy_artifact(xsd, destination, artifact_type="xsd"))

        if schema_target:
            target_relative = Path(schema_target)
            if target_relative.is_absolute():
                msg = "O destino do schema deve ser um caminho relativo dentro de 'schemas/'"
                raise ValueError(msg)

            target_path = (SCHEMAS_DIR / target_relative).resolve()
            schemas_root = SCHEMAS_DIR.resolve()
            if schemas_root not in target_path.parents and target_path != schemas_root:
                msg = (
                    "O caminho fornecido em '--schema-target' precisa residir dentro da pasta 'schemas/'."
                )
                raise ValueError(msg)
            if not target_path.parent.exists():
                msg = f"Directoria destino para schema '{target_path.parent}' não existe"
                raise FileNotFoundError(msg)
            artifacts.append(
                copy_artifact(xsd, target_path, artifact_type="xsd-promoted"),
            )

    for rule_file in rule_files:
        if not rule_file.exists():
            msg = f"Ficheiro de regras '{rule_file}' não encontrado"
            raise FileNotFoundError(msg)
        destination = update_dir / rule_file.name
        artifacts.append(copy_artifact(rule_file, destination, artifact_type="rule"))

    if not artifacts:
        raise ValueError("É necessário fornecer pelo menos um ficheiro para registar a actualização.")

    entry = RuleUpdate(
        identifier=identifier,
        note=note,
        created_at=timestamp.isoformat(),
        tag=tag,
        folder=str(update_dir.relative_to(REPO_ROOT)),
        artifacts=artifacts,
    )

    entries = load_index()
    entries.append(entry)
    entries.sort(key=lambda item: item.created_at)
    save_index(entries)
    return entry


def build_parser() -> argparse.ArgumentParser:
    """Criar o *parser* de argumentos para a ferramenta de sincronização."""

    parser = argparse.ArgumentParser(
        description="Registar actualizações de XSD e regras de negócio SAF-T (AO)",
    )
    parser.add_argument(
        "--note",
        "-n",
        required=True,
        help="Descrição curta da alteração recebida da AGT.",
    )
    parser.add_argument(
        "--xsd",
        type=Path,
        help="Caminho para o novo ficheiro XSD recebido.",
    )
    parser.add_argument(
        "--rule",
        "-r",
        action="append",
        default=[],
        type=Path,
        help="Caminho para um ficheiro de regras adicional (pode ser usado múltiplas vezes).",
    )
    parser.add_argument(
        "--tag",
        help="Etiqueta ou referência interna (por exemplo, número de circular da AGT).",
    )
    parser.add_argument(
        "--schema-target",
        help=(
            "Caminho relativo dentro de 'schemas/' onde o XSD deve ser copiado "
            "para actualizar o esquema activo."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada de linha de comandos."""

    parser = build_parser()
    args = parser.parse_args(argv)

    RULES_DIR.mkdir(parents=True, exist_ok=True)

    entry = register_update(
        note=args.note,
        xsd=args.xsd,
        rule_files=list(args.rule),
        tag=args.tag,
        schema_target=args.schema_target,
    )

    print("Actualização registada:")
    print(f"  ID: {entry.identifier}")
    print(f"  Pasta: {entry.folder}")
    for artifact in entry.artifacts:
        print(f"  - {artifact.type}: {artifact.relative_path} (sha256={artifact.sha256})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
