"""Interface gráfica unificada para as ferramentas SAF-T (AO).

Este módulo disponibiliza uma aplicação em PySide6 que agrega as
funcionalidades principais do projecto num único local: validação do ficheiro
SAF-T, correcções automáticas *soft* e *hard* e registo de novas actualizações
de regras ou esquemas. O objectivo é fornecer uma experiência acessível para
utilizadores que preferem interagir com uma interface gráfica em vez da linha
de comandos.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import (
    QCoreApplication,
    QLibraryInfo,
    QObject,
    Qt,
    QProcess,
    QProcessEnvironment,
    Signal,
    Slot,
)
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
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
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_SCRIPT = REPO_ROOT / "validator_saft_ao.py"
AUTOFIX_SOFT_SCRIPT = REPO_ROOT / "saft_ao_autofix_soft.py"
AUTOFIX_HARD_SCRIPT = REPO_ROOT / "saft_ao_autofix_hard.py"
DEFAULT_XSD = REPO_ROOT / "schemas" / "SAFTAO1.01_01.xsd"


class UserInputError(Exception):
    """Erro de validação provocado por dados introduzidos pelo utilizador."""


_PLUGIN_SUFFIXES = {".dll", ".dylib", ".so"}


def _ensure_qt_plugin_path() -> None:
    """Ensure that Qt can locate the platform plugins when running from a venv."""

    env_path = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH")
    if env_path:
        configured = _resolve_platform_plugin_dir(Path(env_path))
        if configured is not None:
            _configure_qt_plugin_dir(configured)
            return

    plugin_root = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    configured = _resolve_platform_plugin_dir(plugin_root)
    if configured is not None:
        _configure_qt_plugin_dir(configured)


def _configure_qt_plugin_dir(directory: Path) -> None:
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(directory)

    library_paths = {Path(path) for path in QCoreApplication.libraryPaths()}
    if directory not in library_paths:
        QCoreApplication.addLibraryPath(str(directory))


def _resolve_platform_plugin_dir(candidate: Path) -> Path | None:
    """Return the directory that actually contains platform plugins, if any."""

    possible_directories = []
    if candidate.name == "platforms":
        possible_directories.append(candidate)
    else:
        possible_directories.append(candidate / "platforms")
        possible_directories.append(candidate)

    for directory in possible_directories:
        if not directory.is_dir():
            continue

        for entry in directory.iterdir():
            if entry.is_file() and entry.suffix.lower() in _PLUGIN_SUFFIXES:
                name = entry.stem.lower()
                if name.startswith("q") or name.startswith("libq"):
                    return directory

    return None


def _create_path_selector(line_edit: QLineEdit, button: QPushButton) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(line_edit)
    layout.addWidget(button)
    return container


class CommandRunner(QObject):
    """Executa comandos externos de forma assíncrona usando ``QProcess``."""

    started = Signal(str)
    output_received = Signal(str)
    error_received = Signal(str)
    finished = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
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
            self._pending_command_repr = None

    @Slot()
    def _handle_stdout(self) -> None:
        if self._process is None:
            return
        text = bytes(self._process.readAllStandardOutput()).decode("utf-8", "ignore")
        if text:
            self.output_received.emit(text)

    @Slot()
    def _handle_stderr(self) -> None:
        if self._process is None:
            return
        text = bytes(self._process.readAllStandardError()).decode("utf-8", "ignore")
        if text:
            self.error_received.emit(text)

    @Slot(int, QProcess.ExitStatus)
    def _handle_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:
        self._cleanup(exit_code)

    @Slot(QProcess.ProcessError)
    def _handle_error(self, error: QProcess.ProcessError) -> None:
        if self._process is None:
            return
        message = self._process.errorString()
        if message:
            self.error_received.emit(message + "\n")
        if error == QProcess.ProcessError.FailedToStart:
            self._cleanup(-1)

    def _cleanup(self, exit_code: int) -> None:
        process = self._process
        if process is None:
            return
        process.deleteLater()
        self._process = None
        self.finished.emit(exit_code)


class OperationTab(QWidget):
    """Base para *tabs* que executam comandos externos."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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
            QMessageBox.information(
                self,
                "Operação em curso",
                "Já existe uma operação a decorrer. Aguarde o seu término.",
            )
            return

        try:
            arguments, cwd = self.build_command()
        except UserInputError as exc:
            QMessageBox.warning(self, "Dados em falta", str(exc))
            return

        self.output.clear()
        if not self.runner.run(sys.executable, arguments, cwd=cwd):
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

    @Slot(int)
    def _on_finished(self, exit_code: int) -> None:
        if self._run_button is not None:
            self._run_button.setEnabled(True)
        if exit_code == 0:
            self.status_label.setText("Concluído com sucesso.")
        else:
            self.status_label.setText(f"Concluído com código {exit_code}.")

    @Slot(str)
    def _append_output(self, text: str) -> None:
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()


class ValidationTab(OperationTab):
    """Executa a validação completa do ficheiro SAF-T."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.xml_edit = QLineEdit()
        self.xsd_edit = QLineEdit(str(DEFAULT_XSD) if DEFAULT_XSD.exists() else "")

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
        layout.addWidget(self.status_label)
        layout.addWidget(self.output)

    def _select_xml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar ficheiro SAF-T",
            str(Path.home()),
            "Ficheiros SAF-T (*.xml);;Todos os ficheiros (*)",
        )
        if path:
            self.xml_edit.setText(path)

    def _select_xsd(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar ficheiro XSD",
            str(DEFAULT_XSD.parent if DEFAULT_XSD.exists() else Path.home()),
            "Ficheiros XSD (*.xsd);;Todos os ficheiros (*)",
        )
        if path:
            self.xsd_edit.setText(path)

    def build_command(self) -> tuple[list[str], Path | None]:
        xml_path = self._require_existing_path(self.xml_edit.text(), "ficheiro SAF-T")
        arguments = [str(VALIDATOR_SCRIPT), str(xml_path)]

        xsd_text = self.xsd_edit.text().strip()
        if xsd_text:
            xsd_path = self._require_existing_path(xsd_text, "ficheiro XSD")
            arguments.extend(["--xsd", str(xsd_path)])

        return arguments, xml_path.parent

    @staticmethod
    def _require_existing_path(value: str, description: str) -> Path:
        text = value.strip()
        if not text:
            raise UserInputError(f"Selecione um {description}.")
        path = Path(text).expanduser()
        if not path.exists():
            raise UserInputError(f"O {description} '{path}' não foi encontrado.")
        return path


class AutoFixTab(OperationTab):
    """Base para *tabs* de execução dos scripts de auto-correcção."""

    def __init__(self, script_path: Path, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._script_path = script_path
        self.xml_edit = QLineEdit()

        xml_button = QPushButton("Escolher ficheiro…")
        xml_button.clicked.connect(self._select_xml)

        run_button = QPushButton(label)
        self.register_run_button(run_button)

        description = QLabel(
            "O resultado (XML corrigido e log em Excel) é gravado na mesma pasta do ficheiro original."
        )
        description.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Ficheiro SAF-T:", _create_path_selector(self.xml_edit, xml_button))

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(description)
        layout.addWidget(run_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.output)

    def _select_xml(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar ficheiro SAF-T",
            str(Path.home()),
            "Ficheiros SAF-T (*.xml);;Todos os ficheiros (*)",
        )
        if path:
            self.xml_edit.setText(path)

    def build_command(self) -> tuple[list[str], Path | None]:
        xml_path = self._require_existing_path(self.xml_edit.text())
        return [str(self._script_path), str(xml_path)], xml_path.parent

    @staticmethod
    def _require_existing_path(value: str) -> Path:
        text = value.strip()
        if not text:
            raise UserInputError("Selecione um ficheiro SAF-T.")
        path = Path(text).expanduser()
        if not path.exists():
            raise UserInputError(f"O ficheiro '{path}' não foi encontrado.")
        return path


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

        if not xsd_text and not rules:
            raise UserInputError(
                "Adicione pelo menos um ficheiro (XSD ou regras) para registar a actualização."
            )

        return arguments, REPO_ROOT

    @staticmethod
    def _require_existing(value: str, description: str) -> Path:
        path = Path(value).expanduser()
        if not path.exists():
            raise UserInputError(f"O {description} '{path}' não foi encontrado.")
        return path


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ferramentas SAF-T (AO)")

        tabs = QTabWidget()
        tabs.addTab(ValidationTab(), "Validação")
        tabs.addTab(AutoFixTab(AUTOFIX_SOFT_SCRIPT, "Executar Auto-Fix Soft"), "Auto-Fix Soft")
        tabs.addTab(AutoFixTab(AUTOFIX_HARD_SCRIPT, "Executar Auto-Fix Hard"), "Auto-Fix Hard")
        tabs.addTab(RuleUpdateTab(), "Actualizações de regras")

        self.setCentralWidget(tabs)
        self.resize(1000, 720)


def main() -> int:
    _ensure_qt_plugin_path()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
