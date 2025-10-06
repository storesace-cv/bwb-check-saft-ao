"""Interface gráfica unificada para as ferramentas SAF-T (AO).

Este módulo disponibiliza uma aplicação em PySide6 que agrega as
funcionalidades principais do projecto num único local: validação do ficheiro
SAF-T, correcções automáticas *soft* e *hard* e registo de novas actualizações
de regras ou esquemas. O objectivo é fornecer uma experiência acessível para
utilizadores que preferem interagir com uma interface gráfica em vez da linha
de comandos.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
import shutil
import sys
from functools import partial
from pathlib import Path
from typing import Iterable, Mapping

from PySide6.QtCore import (
    QCoreApplication,
    QLibraryInfo,
    QObject,
    QSettings,
    Qt,
    QProcess,
    QProcessEnvironment,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QTextCursor
from PySide6.QtWidgets import (
    QAction,
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


QAction = QtGui.QAction


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
VALIDATOR_SCRIPT = SCRIPTS_DIR / "validator_saft_ao.py"
AUTOFIX_SOFT_SCRIPT = SCRIPTS_DIR / "saft_ao_autofix_soft.py"
AUTOFIX_HARD_SCRIPT = SCRIPTS_DIR / "saft_ao_autofix_hard.py"
DEFAULT_XSD = REPO_ROOT / "schemas" / "SAFTAO1.01_01.xsd"
LOG_DIR = REPO_ROOT / "work" / "logs"
LOG_FILE = LOG_DIR / "saftao_gui.log"


def _configure_logging() -> logging.Logger:
    """Configure application-wide logging to a rotating file."""

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("saftao.gui")
    if not logger.handlers:
        handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    logging.captureWarnings(True)
    return logger


LOGGER = _configure_logging()


class UserInputError(Exception):
    """Erro de validação provocado por dados introduzidos pelo utilizador."""


_PLUGIN_SUFFIXES = {".dll", ".dylib", ".so"}


def _ensure_qt_plugin_path() -> None:
    """Guarantee that Qt can locate platform plugins even inside venvs."""

    discovered = _discover_platform_plugin_dirs()
    if discovered is None:
        LOGGER.warning("Não foi possível localizar plugins Qt adicionais.")
        return

    plugin_root, platform_dir = discovered
    LOGGER.debug("Qt plugins detectados em %s", plugin_root)

    os.environ["QT_PLUGIN_PATH"] = str(plugin_root)
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platform_dir)
    LOGGER.debug("QT_PLUGIN_PATH ajustado para %s", plugin_root)
    LOGGER.debug("QT_QPA_PLATFORM_PLUGIN_PATH ajustado para %s", platform_dir)

    existing_paths = {Path(path) for path in QCoreApplication.libraryPaths()}
    for directory in (plugin_root, platform_dir):
        if directory not in existing_paths:
            QCoreApplication.addLibraryPath(str(directory))
            existing_paths.add(directory)
            LOGGER.debug("Adicionado %s às library paths do Qt", directory)


def _discover_platform_plugin_dirs() -> tuple[Path, Path] | None:
    """Return ``(plugin_root, platform_dir)`` if any candidate contains plugins."""

    for candidate in _iter_plugin_roots():
        platform_dir = candidate / "platforms"
        if _contains_platform_plugins(platform_dir):
            return candidate, platform_dir

        if candidate.name == "platforms" and _contains_platform_plugins(candidate):
            return candidate.parent, candidate

    return None


def _iter_plugin_roots() -> Iterable[Path]:
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
            if env_name == "QT_QPA_PLATFORM_PLUGIN_PATH" and path.name == "platforms":
                yield path.parent
            else:
                yield path

    qt_plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)).resolve()
    if qt_plugins not in seen:
        seen.add(qt_plugins)
        yield qt_plugins

    try:
        import PySide6  # type: ignore
    except ImportError:  # pragma: no cover - PySide6 is an explicit dependency
        pass
    else:
        pyside_root = Path(PySide6.__file__).resolve().parent
        for relative in (Path("Qt/plugins"), Path("plugins")):
            candidate = (pyside_root / relative).resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            yield candidate


def _contains_platform_plugins(directory: Path) -> bool:
    if not directory.is_dir():
        return False

    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        suffix = entry.suffix.lower()
        if suffix in _PLUGIN_SUFFIXES:
            name = entry.stem.lower()
            if name.startswith("q") or name.startswith("libq"):
                return True
    return False


def _create_path_selector(line_edit: QLineEdit, button: QPushButton) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(line_edit)
    layout.addWidget(button)
    return container


class DefaultFolderManager(QObject):
    """Persiste e divulga as pastas padrão utilizadas pelas operações."""

    folder_changed = Signal(str, Path)

    FOLDER_ORIGIN = "origin"
    FOLDER_VALIDATION = "validation"
    FOLDER_FIX_STANDARD = "fix_standard"
    FOLDER_FIX_HIGH = "fix_high"

    _SETTINGS_PREFIX = "folders"
    _DEFAULTS: Mapping[str, Path] = {
        FOLDER_ORIGIN: REPO_ROOT / "work" / "origem",
        FOLDER_VALIDATION: REPO_ROOT / "work" / "destino" / "verify",
        FOLDER_FIX_STANDARD: REPO_ROOT / "work" / "destino" / "std",
        FOLDER_FIX_HIGH: REPO_ROOT / "work" / "destino" / "hard",
    }

    _LABELS: Mapping[str, str] = {
        FOLDER_ORIGIN: "Pasta de origem (ficheiros originais)",
        FOLDER_VALIDATION: "Destino da validação",
        FOLDER_FIX_STANDARD: "Destino Fix Precisão Standard",
        FOLDER_FIX_HIGH: "Destino Fix Precisão Alta",
    }

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._logger = LOGGER.getChild("DefaultFolderManager")
        self._logger.info("Inicializar gestor de pastas por defeito.")
        self._settings = QSettings("bwb", "saftao_gui")
        self._ensure_structure()

    def keys(self) -> tuple[str, ...]:
        return tuple(self._DEFAULTS.keys())

    def label_for(self, key: str) -> str:
        try:
            return self._LABELS[key]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"Unknown folder key: {key}") from exc

    def get_folder(self, key: str) -> Path:
        default = self._get_default(key)
        stored = self._settings.value(self._settings_key(key))
        if stored:
            path = Path(str(stored)).expanduser()
        else:
            path = default
        path.mkdir(parents=True, exist_ok=True)
        resolved = path.resolve()
        self._logger.debug("Pasta '%s' resolvida para %s", key, resolved)
        return resolved

    def set_folder(self, key: str, value: Path | str) -> Path:
        new_path = Path(value).expanduser()
        new_path.mkdir(parents=True, exist_ok=True)
        new_path = new_path.resolve()
        current = self.get_folder(key)
        if current == new_path:
            self._logger.debug("Pasta '%s' já configurada para %s", key, new_path)
            return current
        self._settings.setValue(self._settings_key(key), str(new_path))
        self._logger.info("Pasta '%s' actualizada para %s", key, new_path)
        self.folder_changed.emit(key, new_path)
        return new_path

    def reset_to_defaults(self) -> None:
        for key, path in self._DEFAULTS.items():
            self._logger.info("Repor pasta '%s' para %s", key, path)
            self.set_folder(key, path)

    def _settings_key(self, key: str) -> str:
        return f"{self._SETTINGS_PREFIX}/{key}"

    def _get_default(self, key: str) -> Path:
        try:
            return self._DEFAULTS[key]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"Unknown folder key: {key}") from exc

    def _ensure_structure(self) -> None:
        for path in self._DEFAULTS.values():
            path.mkdir(parents=True, exist_ok=True)
            self._logger.debug("Garantida existência da pasta %s", path)


class CommandRunner(QObject):
    """Executa comandos externos de forma assíncrona usando ``QProcess``."""

    started = Signal(str)
    output_received = Signal(str)
    error_received = Signal(str)
    finished = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._logger = LOGGER.getChild("CommandRunner")
        self._process: QProcess | None = None
        self._pending_command_repr: str | None = None

    def is_running(self) -> bool:
        return bool(self._process and self._process.state() != QProcess.NotRunning)

    def run(
        self,
        program: str,
        arguments: Iterable[str],
        *,
        cwd: Path | None = None,
    ) -> bool:
        if self.is_running():
            self._logger.warning(
                "Tentativa de executar '%s' enquanto outro processo decorre.", program
            )
            return False

        process = QProcess(self)
        if cwd is not None:
            process.setWorkingDirectory(str(cwd))

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        process.setProcessEnvironment(env)

        process.setProgram(program)
        arguments = list(arguments)
        process.setArguments(arguments)

        process.readyReadStandardOutput.connect(self._handle_stdout)
        process.readyReadStandardError.connect(self._handle_stderr)
        process.finished.connect(self._handle_finished)
        process.errorOccurred.connect(self._handle_error)
        process.started.connect(self._handle_started)

        self._process = process
        self._pending_command_repr = self._format_command(program, arguments)
        self._logger.info("A iniciar comando: %s", self._pending_command_repr)
        process.start()
        return True

    @staticmethod
    def _format_command(program: str, arguments: Iterable[str]) -> str:
        def quote(value: str) -> str:
            if not value or any(ch.isspace() for ch in value) or '"' in value:
                escaped = value.replace("\"", '\\"')
                return f'"{escaped}"'
            return value

        return " ".join([quote(program), *(quote(arg) for arg in arguments)])

    @Slot()
    def _handle_started(self) -> None:
        if self._pending_command_repr is not None:
            self.started.emit(self._pending_command_repr)
            self._logger.info("Comando iniciado: %s", self._pending_command_repr)
            self._pending_command_repr = None

    @Slot()
    def _handle_stdout(self) -> None:
        if self._process is None:
            return
        text = bytes(self._process.readAllStandardOutput()).decode("utf-8", "ignore")
        if text:
            self.output_received.emit(text)
            self._logger.debug("STDOUT: %s", text.rstrip())

    @Slot()
    def _handle_stderr(self) -> None:
        if self._process is None:
            return
        text = bytes(self._process.readAllStandardError()).decode("utf-8", "ignore")
        if text:
            self.error_received.emit(text)
            self._logger.warning("STDERR: %s", text.rstrip())

    @Slot(int, QProcess.ExitStatus)
    def _handle_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._cleanup(exit_code)
        self._logger.info("Comando terminado com código %s", exit_code)

    @Slot(QProcess.ProcessError)
    def _handle_error(self, error: QProcess.ProcessError) -> None:
        if self._process is None:
            return
        message = self._process.errorString()
        if message:
            self.error_received.emit(message + "\n")
            self._logger.error("Erro de processo: %s", message)
        if error == QProcess.ProcessError.FailedToStart:
            self._cleanup(-1)

    def _cleanup(self, exit_code: int) -> None:
        process = self._process
        if process is None:
            return
        process.deleteLater()
        self._process = None
        self.finished.emit(exit_code)
        self._logger.debug("Recursos do processo libertados.")


class OperationTab(QWidget):
    """Base para *tabs* que executam comandos externos."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._logger = LOGGER.getChild(self.__class__.__name__)
        self.runner = CommandRunner(self)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.status_label = QLabel("Pronto.")
        self._run_button: QPushButton | None = None

        self.runner.output_received.connect(self._append_output)
        self.runner.error_received.connect(self._append_output)
        self.runner.started.connect(self._on_started)
        self.runner.finished.connect(self._on_finished)

    def register_run_button(self, button: QPushButton) -> None:
        self._run_button = button
        button.clicked.connect(self._on_run_clicked)

    def build_command(self) -> tuple[list[str], Path | None]:
        raise NotImplementedError

    def _on_run_clicked(self) -> None:
        if self.runner.is_running():
            self._logger.warning("Pedido de execução ignorado: processo já em curso.")
            QMessageBox.information(
                self,
                "Operação em curso",
                "Já existe uma operação a decorrer. Aguarde o seu término.",
            )
            return

        try:
            arguments, cwd = self.build_command()
        except UserInputError as exc:
            self._logger.warning("Validação falhou: %s", exc)
            QMessageBox.warning(self, "Dados em falta", str(exc))
            return
        except Exception:  # pragma: no cover - via interface
            self._logger.exception("Erro inesperado ao preparar a operação.")
            QMessageBox.critical(
                self,
                "Erro inesperado",
                (
                    "Ocorreu um erro inesperado durante a preparação da operação. "
                    f"Consulte o log em {LOG_FILE} para mais detalhes."
                ),
            )
            return

        self.output.clear()
        self._logger.info("A executar comando com argumentos: %s", arguments)
        if not self.runner.run(sys.executable, arguments, cwd=cwd):
            self._logger.warning("Falha ao iniciar processo: outro processo em execução.")
            QMessageBox.warning(
                self,
                "Operação em curso",
                "Já existe uma operação a decorrer. Aguarde o seu término.",
            )
            return

        if self._run_button is not None:
            self._run_button.setEnabled(False)

    @Slot(str)
    def _on_started(self, command: str) -> None:
        self.status_label.setText("A executar…")
        self.output.appendPlainText(f"$ {command}")
        self._logger.info("Execução iniciada: %s", command)

    @Slot(int)
    def _on_finished(self, exit_code: int) -> None:
        if self._run_button is not None:
            self._run_button.setEnabled(True)
        if exit_code == 0:
            self.status_label.setText("Concluído com sucesso.")
            self._logger.info("Execução concluída com sucesso.")
        else:
            self.status_label.setText(f"Concluído com código {exit_code}.")
            self._logger.warning("Execução terminada com código %s", exit_code)

    @Slot(str)
    def _append_output(self, text: str) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()
        self._logger.debug("Output acumulado: %s", text.rstrip())


class ValidationTab(OperationTab):
    """Executa a validação completa do ficheiro SAF-T."""

    def __init__(
        self,
        folders: DefaultFolderManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._folders = folders
        self.xml_edit = QLineEdit()
        self.xsd_edit = QLineEdit(str(DEFAULT_XSD) if DEFAULT_XSD.exists() else "")
        self.destination_label = QLabel()
        self.destination_label.setWordWrap(True)

        xml_button = QPushButton("Escolher ficheiro…")
        xml_button.clicked.connect(self._select_xml)
        xsd_button = QPushButton("Escolher XSD…")
        xsd_button.clicked.connect(self._select_xsd)

        run_button = QPushButton("Executar validação")
        self.register_run_button(run_button)

        form = QFormLayout()
        form.addRow("Ficheiro SAF-T:", _create_path_selector(self.xml_edit, xml_button))
        form.addRow("Ficheiro XSD (opcional):", _create_path_selector(self.xsd_edit, xsd_button))

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(run_button)
        layout.addWidget(self.destination_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.output)

        self._folders.folder_changed.connect(self._on_folder_changed)
        self._update_destination_label()

    def _select_xml(self) -> None:
        base_dir = self._folders.get_folder(DefaultFolderManager.FOLDER_ORIGIN)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar ficheiro SAF-T",
            str(base_dir),
            "Ficheiros SAF-T (*.xml);;Todos os ficheiros (*)",
        )
        if path:
            self.xml_edit.setText(path)
            self._logger.info("Ficheiro SAF-T selecionado: %s", path)

    def _select_xsd(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar ficheiro XSD",
            str(DEFAULT_XSD.parent if DEFAULT_XSD.exists() else Path.home()),
            "Ficheiros XSD (*.xsd);;Todos os ficheiros (*)",
        )
        if path:
            self.xsd_edit.setText(path)
            self._logger.info("Ficheiro XSD selecionado: %s", path)

    def build_command(self) -> tuple[list[str], Path | None]:
        xml_path = self._require_existing_path(self.xml_edit.text(), "ficheiro SAF-T")
        arguments = [str(VALIDATOR_SCRIPT), str(xml_path)]

        xsd_text = self.xsd_edit.text().strip()
        if xsd_text:
            xsd_path = self._require_existing_path(xsd_text, "ficheiro XSD")
            arguments.extend(["--xsd", str(xsd_path)])

        destination = self._folders.get_folder(DefaultFolderManager.FOLDER_VALIDATION)
        self._logger.info(
            "Validação preparada para %s com destino %s", xml_path, destination
        )
        return arguments, destination

    @staticmethod
    def _require_existing_path(value: str, description: str) -> Path:
        text = value.strip()
        if not text:
            raise UserInputError(f"Selecione um {description}.")
        path = Path(text).expanduser()
        if not path.exists():
            raise UserInputError(f"O {description} '{path}' não foi encontrado.")
        LOGGER.debug("Validado %s em %s", description, path)
        return path

    def _update_destination_label(self) -> None:
        destination = self._folders.get_folder(DefaultFolderManager.FOLDER_VALIDATION)
        self.destination_label.setText(
            f"Os resultados (ficheiro Excel de log) são gravados em: {destination}"
        )

    def _on_folder_changed(self, key: str, _path: Path) -> None:
        if key == DefaultFolderManager.FOLDER_VALIDATION:
            self._update_destination_label()


class AutoFixTab(OperationTab):
    """Base para *tabs* de execução dos scripts de auto-correcção."""

    def __init__(
        self,
        script_path: Path,
        label: str,
        folders: DefaultFolderManager,
        destination_key: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._script_path = script_path
        self._folders = folders
        self._destination_key = destination_key
        self.xml_edit = QLineEdit()
        self.destination_label = QLabel()
        self.destination_label.setWordWrap(True)

        xml_button = QPushButton("Escolher ficheiro…")
        xml_button.clicked.connect(self._select_xml)

        run_button = QPushButton(label)
        self.register_run_button(run_button)

        description = QLabel(
            "O ficheiro selecionado é copiado para a pasta de destino configurada "
            "antes da execução. Os resultados (XML corrigido e log em Excel) "
            "são gravados nessa pasta."
        )
        description.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Ficheiro SAF-T:", _create_path_selector(self.xml_edit, xml_button))

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(description)
        layout.addWidget(run_button)
        layout.addWidget(self.destination_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.output)

        self._folders.folder_changed.connect(self._on_folder_changed)
        self._update_destination_label()

    def _select_xml(self) -> None:
        base_dir = self._folders.get_folder(DefaultFolderManager.FOLDER_ORIGIN)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar ficheiro SAF-T",
            str(base_dir),
            "Ficheiros SAF-T (*.xml);;Todos os ficheiros (*)",
        )
        if path:
            self.xml_edit.setText(path)
            self._logger.info("Ficheiro SAF-T selecionado para auto-fix: %s", path)

    def build_command(self) -> tuple[list[str], Path | None]:
        xml_path = self._require_existing_path(self.xml_edit.text())
        destination_dir = self._folders.get_folder(self._destination_key)
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_file = destination_dir / xml_path.name

        if destination_file.exists():
            answer = QMessageBox.question(
                self,
                "Substituir ficheiro?",
                (
                    "Já existe um ficheiro com o mesmo nome na pasta de destino. "
                    "Pretende substituí-lo?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                raise UserInputError("Operação cancelada pelo utilizador.")

        try:
            shutil.copy2(xml_path, destination_file)
        except OSError as exc:  # pragma: no cover - interação com FS
            raise UserInputError(
                f"Não foi possível copiar o ficheiro para '{destination_file}': {exc}"
            ) from exc

        self._logger.info(
            "Ficheiro copiado para %s. Execução preparada no destino %s",
            destination_file,
            destination_dir,
        )
        return [str(self._script_path), str(destination_file)], destination_dir

    @staticmethod
    def _require_existing_path(value: str) -> Path:
        text = value.strip()
        if not text:
            raise UserInputError("Selecione um ficheiro SAF-T.")
        path = Path(text).expanduser()
        if not path.exists():
            raise UserInputError(f"O ficheiro '{path}' não foi encontrado.")
        return path

    def _update_destination_label(self) -> None:
        destination_dir = self._folders.get_folder(self._destination_key)
        self.destination_label.setText(
            f"O ficheiro selecionado será copiado para: {destination_dir}"
        )

    def _on_folder_changed(self, key: str, _path: Path) -> None:
        if key == self._destination_key or key == DefaultFolderManager.FOLDER_ORIGIN:
            self._update_destination_label()


class RuleUpdateTab(OperationTab):
    """Interface para o utilitário de registo de actualizações de regras."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.note_edit = QLineEdit()
        self.tag_edit = QLineEdit()
        self.schema_target_edit = QLineEdit()
        self.xsd_edit = QLineEdit()
        self.rules_list = QListWidget()

        xsd_button = QPushButton("Escolher XSD…")
        xsd_button.clicked.connect(self._select_xsd)

        add_rule_button = QPushButton("Adicionar ficheiros de regras…")
        add_rule_button.clicked.connect(self._add_rule_files)
        remove_rule_button = QPushButton("Remover selecionados")
        remove_rule_button.clicked.connect(self._remove_selected_rules)

        run_button = QPushButton("Registar actualização")
        self.register_run_button(run_button)

        form = QFormLayout()
        form.addRow("Nota:", self.note_edit)
        form.addRow("Etiqueta (opcional):", self.tag_edit)
        form.addRow(
            "Destino schema (opcional):",
            QLabel("Ex.: SAFTAO1.01_01.xsd ou subpastas dentro de 'schemas/'."),
        )
        form.addRow("", self.schema_target_edit)
        form.addRow(
            "Ficheiro XSD (opcional):",
            _create_path_selector(self.xsd_edit, xsd_button),
        )

        rules_box = QGroupBox("Ficheiros de regras")
        rules_layout = QVBoxLayout(rules_box)
        rules_layout.addWidget(self.rules_list)
        button_row = QHBoxLayout()
        button_row.addWidget(add_rule_button)
        button_row.addWidget(remove_rule_button)
        rules_layout.addLayout(button_row)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(rules_box)
        layout.addWidget(run_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.output)

    def _select_xsd(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar ficheiro XSD",
            str(Path.home()),
            "Ficheiros XSD (*.xsd);;Todos os ficheiros (*)",
        )
        if path:
            self.xsd_edit.setText(path)

    def _add_rule_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar ficheiros de regras",
            str(Path.home()),
            "Todos os ficheiros (*)",
        )
        existing = {self.rules_list.item(i).data(Qt.UserRole) for i in range(self.rules_list.count())}
        for path in paths:
            if path and path not in existing:
                item = QListWidgetItem(Path(path).name)
                item.setData(Qt.UserRole, path)
                self.rules_list.addItem(item)

    def _remove_selected_rules(self) -> None:
        for item in self.rules_list.selectedItems():
            row = self.rules_list.row(item)
            self.rules_list.takeItem(row)

    def build_command(self) -> tuple[list[str], Path | None]:
        note = self.note_edit.text().strip()
        if not note:
            raise UserInputError("Indique uma nota descritiva para a actualização.")

        arguments: list[str] = ["-m", "saftao.rules_updates", "--note", note]
        self._logger.info("Preparar registo de regras: nota '%s'", note)

        tag = self.tag_edit.text().strip()
        if tag:
            arguments.extend(["--tag", tag])

        schema_target = self.schema_target_edit.text().strip()
        if schema_target:
            arguments.extend(["--schema-target", schema_target])

        xsd_text = self.xsd_edit.text().strip()
        if xsd_text:
            xsd_path = self._require_existing(xsd_text, "ficheiro XSD")
            arguments.extend(["--xsd", str(xsd_path)])

        rules = [self.rules_list.item(i).data(Qt.UserRole) for i in range(self.rules_list.count())]
        for rule in rules:
            arguments.extend(["--rule", rule])
            self._logger.debug("Regra incluída: %s", rule)

        if not xsd_text and not rules:
            raise UserInputError(
                "Adicione pelo menos um ficheiro (XSD ou regras) para registar a actualização."
            )

        self._logger.info(
            "Actualização de regras preparada com %d ficheiros de regras.", len(rules)
        )
        return arguments, REPO_ROOT

    @staticmethod
    def _require_existing(value: str, description: str) -> Path:
        path = Path(value).expanduser()
        if not path.exists():
            raise UserInputError(f"O {description} '{path}' não foi encontrado.")
        return path


class DefaultFoldersWidget(QWidget):
    """Permite configurar as pastas por defeito utilizadas pelas operações."""

    def __init__(
        self,
        folders: DefaultFolderManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._folders = folders
        self._edits: dict[str, QLineEdit] = {}
        self._logger = LOGGER.getChild("DefaultFoldersWidget")

        description = QLabel(
            "Configure abaixo as pastas por defeito utilizadas para abrir e "
            "guardar ficheiros. As pastas são criadas automaticamente caso "
            "não existam."
        )
        description.setWordWrap(True)

        form = QFormLayout()
        for key in self._folders.keys():
            edit = QLineEdit(str(self._folders.get_folder(key)))
            self._edits[key] = edit
            browse_button = QPushButton("Escolher pasta…")
            browse_button.clicked.connect(partial(self._select_folder, key))
            form.addRow(
                f"{self._folders.label_for(key)}:",
                _create_path_selector(edit, browse_button),
            )

        save_button = QPushButton("Guardar alterações")
        save_button.clicked.connect(self._save_changes)
        reset_button = QPushButton("Repor valores por defeito")
        reset_button.clicked.connect(self._reset_defaults)

        button_row = QHBoxLayout()
        button_row.addWidget(save_button)
        button_row.addWidget(reset_button)
        button_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(description)
        layout.addLayout(form)
        layout.addLayout(button_row)
        layout.addStretch(1)

        self._folders.folder_changed.connect(self._on_folder_changed)

    def _select_folder(self, key: str) -> None:
        current_text = self._edits[key].text().strip()
        current = Path(current_text).expanduser() if current_text else Path.home()
        base_dir = current if current.exists() else Path.home()
        path = QFileDialog.getExistingDirectory(
            self,
            "Selecionar pasta",
            str(base_dir),
        )
        if path:
            self._edits[key].setText(path)
            self._logger.info("Pasta seleccionada para '%s': %s", key, path)

    def _save_changes(self) -> None:
        new_values: dict[str, Path] = {}
        for key, edit in self._edits.items():
            text = edit.text().strip()
            if not text:
                QMessageBox.warning(
                    self,
                    "Pasta inválida",
                    "Indique um caminho válido para todas as pastas.",
                )
                self._logger.warning("Tentativa de guardar com pasta vazia em '%s'", key)
                return
            new_values[key] = Path(text).expanduser()

        try:
            for key, path in new_values.items():
                self._folders.set_folder(key, path)
        except OSError as exc:  # pragma: no cover - depende do FS
            QMessageBox.critical(
                self,
                "Erro ao guardar",
                f"Não foi possível atualizar as pastas: {exc}",
            )
            self._logger.exception("Falha ao actualizar pastas: %s", exc)
            return

        QMessageBox.information(self, "Pastas actualizadas", "Alterações guardadas com sucesso.")
        self._logger.info("Pastas por defeito actualizadas: %s", new_values)
        self._reload_from_manager()

    def _reset_defaults(self) -> None:
        self._folders.reset_to_defaults()
        self._reload_from_manager()
        QMessageBox.information(
            self,
            "Valores repostos",
            "Foram repostas as pastas sugeridas pela aplicação.",
        )
        self._logger.info("Pastas por defeito repostas para os valores iniciais.")

    def _reload_from_manager(self) -> None:
        for key, edit in self._edits.items():
            edit.setText(str(self._folders.get_folder(key)))
        self._logger.debug("Campos de pastas actualizados a partir do gestor.")

    def _on_folder_changed(self, key: str, path: Path) -> None:
        edit = self._edits.get(key)
        if edit is not None:
            edit.setText(str(path))
            self._logger.debug("Interface sincronizada para '%s' com %s", key, path)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ferramentas SAF-T (AO)")
        self._logger = LOGGER.getChild("MainWindow")
        self._logger.info("Inicialização da janela principal.")
        self._folders = DefaultFolderManager(self)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._page_indices: dict[str, int] = {}
        self._register_page(
            "validation",
            ValidationTab(self._folders),
        )
        self._register_page(
            "fix_standard",
            AutoFixTab(
                AUTOFIX_SOFT_SCRIPT,
                "Executar Fix Precisão Standard",
                self._folders,
                DefaultFolderManager.FOLDER_FIX_STANDARD,
            ),
        )
        self._register_page(
            "fix_high",
            AutoFixTab(
                AUTOFIX_HARD_SCRIPT,
                "Executar Fix Precisão Alta",
                self._folders,
                DefaultFolderManager.FOLDER_FIX_HIGH,
            ),
        )
        self._register_page("rule_updates", RuleUpdateTab())
        self._register_page("default_folders", DefaultFoldersWidget(self._folders))

        menubar = self.menuBar()
        self._build_menus(menubar)

        self.resize(1000, 720)
        self._show_page("validation")
        self._logger.info("Janela principal pronta.")

    def _register_page(self, key: str, widget: QWidget) -> None:
        index = self._stack.addWidget(widget)
        self._page_indices[key] = index
        self._logger.debug("Página '%s' registada no índice %s", key, index)

    def _show_page(self, key: str) -> None:
        index = self._page_indices.get(key)
        if index is not None:
            self._stack.setCurrentIndex(index)
            self._logger.info("Página '%s' apresentada.", key)
        else:
            self._logger.warning("Pedido para mostrar página desconhecida: %s", key)

    def _build_menus(self, menubar: QMenuBar) -> None:
        self._logger.debug("A construir menus da aplicação.")
        validation_menu = menubar.addMenu("Validação")
        self._add_menu_action(
            validation_menu,
            "Validação",
            "validation",
        )

        corrections_menu = menubar.addMenu("Correções")
        self._add_menu_action(
            corrections_menu,
            "Fix Precisão Standard",
            "fix_standard",
        )
        self._add_menu_action(
            corrections_menu,
            "Fix Precisão Alta",
            "fix_high",
        )

        parameters_menu = menubar.addMenu("Parâmetros")
        self._add_menu_action(
            parameters_menu,
            "Actualizações de Regras",
            "rule_updates",
        )
        self._add_menu_action(
            parameters_menu,
            "Pastas por Defeito",
            "default_folders",
        )

    def _add_menu_action(self, menu: QMenu, text: str, key: str) -> QAction:
        action = menu.addAction(text)
        action.triggered.connect(lambda _checked=False, target=key: self._show_page(target))
        self._logger.debug("Acção '%s' adicionada ao menu '%s'", text, menu.title())
        return action


def main() -> int:
    LOGGER.info("Aplicação GUI iniciada.")
    _ensure_qt_plugin_path()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    LOGGER.info("Aplicação terminada com código %s", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
