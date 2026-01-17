"""Interface gráfica em Tkinter para as ferramentas SAF-T (AO).

Esta versão substitui a implementação anterior baseada em Qt/PySide6 por uma
abordagem totalmente suportada pela biblioteca padrão ``tkinter``. A
aplicação continua a disponibilizar as funcionalidades principais: validação
SAF-T, correcções automáticas, certificação de clientes e registo de
actualizações de regras.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from functools import partial
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Iterable, Mapping

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .utils.reporting import default_report_destination

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
VALIDATOR_SCRIPT = SCRIPTS_DIR / "validator_saft_ao.py"
AUTOFIX_SOFT_SCRIPT = SCRIPTS_DIR / "saft_ao_autofix_soft.py"
AUTOFIX_HARD_SCRIPT = SCRIPTS_DIR / "saft_ao_autofix_hard.py"
CLIENT_CERT_SCRIPT = SCRIPTS_DIR / "corrige_clientes_agt.py"
REPORT_SCRIPT = SCRIPTS_DIR / "saft_ao_relatorio_totais.py"
DEFAULT_XSD = REPO_ROOT / "schemas" / "SAFTAO1.01_01.xsd"
LOG_DIR = REPO_ROOT / "work" / "logs"
LOG_FILE = LOG_DIR / "saftao_gui.log"
BACKGROUND_IMAGE = Path(__file__).resolve().parent / "ui" / "bwb-Splash.png"
SETTINGS_FILE = LOG_DIR / "gui_settings.json"
CUSTOMER_EXCEL_ENV = "BWB_SAFTAO_CUSTOMER_FILE"

DEFAULT_XSD_SETTINGS_KEY = "defaults/xsd_file"


class AppSettings:
    """Persist simple key/value pairs in a JSON file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._logger = logging.getLogger("saftao.gui.Settings")
        self._data = self._load()

    def get(self, key: str, default: str | None = None) -> str | None:
        return self._data.get(key, default)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._save()

    def remove(self, key: str) -> None:
        if key in self._data:
            self._data.pop(key)
            self._save()

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            self._logger.warning("Falha a ler definições de %s: %s", self.path, exc)
            return {}
        except OSError as exc:  # pragma: no cover - depende do FS
            self._logger.warning("Não foi possível abrir %s: %s", self.path, exc)
            return {}
        if not isinstance(data, dict):  # pragma: no cover - defensive
            self._logger.warning("Estrutura inesperada no ficheiro de definições.")
            return {}
        return {str(key): str(value) for key, value in data.items()}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as handle:
                json.dump(self._data, handle, indent=2, ensure_ascii=False)
        except OSError as exc:  # pragma: no cover - depende do FS
            self._logger.error("Falha ao guardar definições em %s: %s", self.path, exc)


SETTINGS = AppSettings(SETTINGS_FILE)


def _settings_object() -> AppSettings:
    """Return the shared settings handler."""

    return SETTINGS


def configured_default_xsd_path(*, fallback_to_builtin: bool = True) -> Path | None:
    """Return the XSD configured by the user or the bundled default."""

    settings = _settings_object()
    stored = settings.get(DEFAULT_XSD_SETTINGS_KEY)
    if stored:
        return Path(str(stored)).expanduser()
    if fallback_to_builtin and DEFAULT_XSD.exists():
        return DEFAULT_XSD.resolve()
    return None


def configured_default_xsd_directory() -> Path:
    """Return a sensible directory to start file dialogs for XSD selection."""

    xsd_path = configured_default_xsd_path()
    if xsd_path and xsd_path.exists():
        return xsd_path.parent
    if DEFAULT_XSD.exists():
        return DEFAULT_XSD.parent
    return Path.home()


def store_configured_default_xsd(path: Path | None) -> None:
    """Persist the user defined default XSD path."""

    settings = _settings_object()
    if path is None:
        settings.remove(DEFAULT_XSD_SETTINGS_KEY)
        return
    expanded = Path(path).expanduser()
    settings.set(DEFAULT_XSD_SETTINGS_KEY, str(expanded))


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


FolderChangedCallback = Callable[[str, Path], None]


class DefaultFolderManager:
    """Persiste e divulga as pastas padrão utilizadas pelas operações."""

    FOLDER_ORIGIN = "origin"
    FOLDER_VALIDATION = "validation"
    FOLDER_FIX_STANDARD = "fix_standard"
    FOLDER_FIX_HIGH = "fix_high"
    FOLDER_CLIENT_CERT_SOURCE = "client_cert_source"
    FOLDER_CLIENT_CERT_DESTINATION = "client_cert_destination"
    FOLDER_REPORT_DESTINATION = "report_destination"

    _SETTINGS_PREFIX = "folders"
    _DEFAULTS: Mapping[str, Path] = {
        FOLDER_ORIGIN: REPO_ROOT / "work" / "origem",
        FOLDER_VALIDATION: REPO_ROOT / "work" / "destino" / "verify",
        FOLDER_FIX_STANDARD: REPO_ROOT / "work" / "destino" / "std",
        FOLDER_FIX_HIGH: REPO_ROOT / "work" / "destino" / "hard",
        FOLDER_CLIENT_CERT_SOURCE: REPO_ROOT / "work" / "origem" / "addons",
        FOLDER_CLIENT_CERT_DESTINATION: REPO_ROOT / "work" / "destino" / "clientes",
        FOLDER_REPORT_DESTINATION: REPO_ROOT / "work" / "destino" / "relatorios",
    }

    _LABELS: Mapping[str, str] = {
        FOLDER_ORIGIN: "Pasta de origem (ficheiros originais)",
        FOLDER_VALIDATION: "Destino da validação",
        FOLDER_FIX_STANDARD: "Destino Fix Precisão Standard",
        FOLDER_FIX_HIGH: "Destino Fix Precisão Alta",
        FOLDER_CLIENT_CERT_SOURCE: "Pasta de origem (Excel de clientes)",
        FOLDER_CLIENT_CERT_DESTINATION: "Destino Certifica Clientes",
        FOLDER_REPORT_DESTINATION: "Destino Relatórios de Totais",
    }

    def __init__(self) -> None:
        self._logger = LOGGER.getChild("DefaultFolderManager")
        self._settings = _settings_object()
        self._callbacks: list[FolderChangedCallback] = []
        self._ensure_structure()

    def keys(self) -> tuple[str, ...]:
        return tuple(self._DEFAULTS.keys())

    def label_for(self, key: str) -> str:
        try:
            return self._LABELS[key]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"Unknown folder key: {key}") from exc

    def subscribe(self, callback: FolderChangedCallback) -> None:
        self._callbacks.append(callback)

    def unsubscribe(self, callback: FolderChangedCallback) -> None:
        try:
            self._callbacks.remove(callback)
        except ValueError:  # pragma: no cover - defensive
            pass

    def get_folder(self, key: str) -> Path:
        default = self._get_default(key)
        stored = self._settings.get(self._settings_key(key))
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
        self._settings.set(self._settings_key(key), str(new_path))
        self._logger.info("Pasta '%s' actualizada para %s", key, new_path)
        self._notify(key, new_path)
        return new_path

    def reset_to_defaults(self) -> None:
        for key, path in self._DEFAULTS.items():
            self._logger.info("Repor pasta '%s' para %s", key, path)
            self.set_folder(key, path)

    def _notify(self, key: str, path: Path) -> None:
        for callback in list(self._callbacks):
            try:
                callback(key, path)
            except Exception:  # pragma: no cover - defensive
                self._logger.exception("Callback de pasta '%s' falhou.", key)

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


class CommandRunner:
    """Executa comandos externos em *threads* separadas."""

    def __init__(self, widget: tk.Misc) -> None:
        self._widget = widget
        self._logger = LOGGER.getChild("CommandRunner")
        self._process: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def terminate(self) -> None:
        with self._lock:
            process = self._process
        if process and process.poll() is None:
            self._logger.info("A terminar processo em execução…")
            process.terminate()

    def run(
        self,
        program: str,
        arguments: Iterable[str],
        *,
        cwd: Path | None = None,
        env_overrides: Mapping[str, str | None] | None = None,
        on_started: Callable[[str], None] | None = None,
        on_output: Callable[[str], None] | None = None,
        on_finished: Callable[[int], None] | None = None,
    ) -> bool:
        with self._lock:
            if self.is_running():
                self._logger.warning("Tentativa de executar comando enquanto outro decorre.")
                return False

        arguments = list(arguments)
        command_repr = self._format_command(program, arguments)
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        if env_overrides:
            for key, value in env_overrides.items():
                if value is None:
                    env.pop(key, None)
                else:
                    env[key] = value

        try:
            process = subprocess.Popen(
                [program, *arguments],
                cwd=str(cwd) if cwd is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
            )
        except OSError as exc:
            self._logger.error("Falha ao iniciar processo: %s", exc)
            if on_output is not None:
                self._widget.after(0, on_output, f"Erro ao iniciar processo: {exc}\n")
            return False

        with self._lock:
            self._process = process

        def notify_started() -> None:
            self._logger.info("Comando iniciado: %s", command_repr)
            if on_started is not None:
                on_started(command_repr)

        def pump(pipe: subprocess.PIPE, prefix: str) -> None:  # type: ignore[type-arg]
            assert pipe is not None
            for line in pipe:
                message = line
                if prefix:
                    message = f"[{prefix}] {line}"
                if on_output is not None:
                    self._widget.after(0, on_output, message)
            pipe.close()

        def worker() -> None:
            notify_started()
            stdout_thread = threading.Thread(
                target=pump, args=(process.stdout, ""), daemon=True
            )
            stderr_thread = threading.Thread(
                target=pump, args=(process.stderr, "erro"), daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()
            exit_code = process.wait()
            stdout_thread.join()
            stderr_thread.join()
            self._logger.info("Comando terminado com código %s", exit_code)
            if on_finished is not None:
                self._widget.after(0, on_finished, exit_code)
            with self._lock:
                self._process = None

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
        return True

    @staticmethod
    def _format_command(program: str, arguments: Iterable[str]) -> str:
        def quote(value: str) -> str:
            if not value or any(ch.isspace() for ch in value) or '"' in value:
                escaped = value.replace('"', '\\"')
                return f'"{escaped}"'
            return value

        return " ".join([quote(program), *(quote(arg) for arg in arguments)])


class ReadOnlyScrolledText(scrolledtext.ScrolledText):
    """Scrolled text widget that allows selection but blocks edits."""

    _CONTROL_MASK = 0x0004
    _COMMAND_MASK = 0x100000
    _NAVIGATION_KEYS = {
        "Left",
        "Right",
        "Up",
        "Down",
        "Home",
        "End",
        "Next",
        "Prior",
    }

    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._configure_read_only_behavior()

    def _configure_read_only_behavior(self) -> None:
        def discard(event: tk.Event) -> str:
            return "break"

        self.bind("<Key>", self._on_key_press)
        self.bind("<Button-1>", lambda event: self.focus_set())
        self.bind("<<Copy>>", self._on_copy)
        self.bind("<Command-c>", lambda event: None)
        self.bind("<Command-C>", lambda event: None)
        self.bind("<Command-a>", self._on_command_select_all)
        self.bind("<Command-A>", self._on_command_select_all)
        for sequence in (
            "<<Cut>>",
            "<<Paste>>",
            "<<PasteSelection>>",
            "<Control-v>",
            "<Control-V>",
            "<Control-x>",
            "<Control-X>",
            "<Shift-Insert>",
            "<Button-2>",
        ):
            self.bind(sequence, discard)

    def _on_key_press(self, event: tk.Event) -> str | None:
        control_pressed = bool(event.state & self._CONTROL_MASK)
        command_pressed = bool(event.state & self._COMMAND_MASK)
        keysym = event.keysym

        if (control_pressed or command_pressed) and keysym.lower() == "c":
            return None
        if (control_pressed or command_pressed) and keysym == "Insert":
            return None
        if (control_pressed or command_pressed) and keysym.lower() == "a":
            self.tag_add("sel", "1.0", "end-1c")
            return "break"
        if keysym in self._NAVIGATION_KEYS:
            return None

        return "break"

    def _on_copy(self, event: tk.Event) -> str:
        try:
            selection = self.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"
        self.clipboard_clear()
        self.clipboard_append(selection)
        return "break"

    def _on_command_select_all(self, event: tk.Event) -> str:
        self.tag_add("sel", "1.0", "end-1c")
        return "break"


class OperationTab(ttk.Frame):
    """Base para *tabs* que executam comandos externos."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self._logger = LOGGER.getChild(self.__class__.__name__)
        self.runner = CommandRunner(self)
        self.output_container = ttk.Frame(self)
        self.output = ReadOnlyScrolledText(
            self.output_container, height=14, wrap=tk.WORD
        )
        self.output.configure(background="#f5f5f5", foreground="#202020")
        self.output.pack(fill="both", expand=True)
        style = ttk.Style(self)
        style.configure("CopyLog.TButton", padding=(1, 0))

        self._copy_all_button = ttk.Button(
            self.output_container,
            text="....",
            width=3,
            command=self._copy_all_output,
            takefocus=False,
            style="CopyLog.TButton",
        )
        self._copy_all_button.pack(anchor="e", pady=(4, 0))
        self.status_var = tk.StringVar(value="Pronto.")
        self.status_label = ttk.Label(self, textvariable=self.status_var)
        self._run_button: ttk.Button | None = None

    def register_run_button(self, button: ttk.Button) -> None:
        self._run_button = button
        button.configure(command=self._on_run_clicked)

    def build_command(self) -> tuple[list[str], Path | None]:
        raise NotImplementedError

    def env_overrides(self) -> Mapping[str, str | None] | None:
        return None

    def cleanup(self) -> None:
        self.runner.terminate()

    def _on_run_clicked(self) -> None:
        if self.runner.is_running():
            self._logger.warning("Pedido de execução ignorado: processo já em curso.")
            messagebox.showinfo(
                "Operação em curso",
                "Já existe uma operação a decorrer. Aguarde o seu término.",
            )
            return

        try:
            arguments, cwd = self.build_command()
        except UserInputError as exc:
            self._logger.warning("Validação falhou: %s", exc)
            messagebox.showwarning("Dados em falta", str(exc))
            return
        except Exception:  # pragma: no cover - via interface
            self._logger.exception("Erro inesperado ao preparar a operação.")
            messagebox.showerror(
                "Erro inesperado",
                (
                    "Ocorreu um erro inesperado durante a preparação da operação. "
                    f"Consulte o log em {LOG_FILE} para mais detalhes."
                ),
            )
            return

        self._clear_output()
        self._logger.info("A executar comando com argumentos: %s", arguments)
        env_overrides = self.env_overrides()
        if not self.runner.run(
            sys.executable,
            arguments,
            cwd=cwd,
            env_overrides=env_overrides,
            on_started=self._on_started,
            on_output=self._append_output,
            on_finished=self._on_finished,
        ):
            self._logger.warning("Falha ao iniciar processo: outro processo em execução.")
            messagebox.showwarning(
                "Operação em curso",
                "Já existe uma operação a decorrer. Aguarde o seu término.",
            )
            return

        if self._run_button is not None:
            self._run_button.configure(state=tk.DISABLED)

    def _on_started(self, command: str) -> None:
        self.status_var.set("A executar…")
        self._append_output(f"$ {command}\n")
        self._logger.info("Execução iniciada: %s", command)

    def _on_finished(self, exit_code: int) -> None:
        if self._run_button is not None:
            self._run_button.configure(state=tk.NORMAL)
        if exit_code == 0:
            self.status_var.set("Concluído com sucesso.")
            self._logger.info("Execução concluída com sucesso.")
        else:
            self.status_var.set(f"Concluído com código {exit_code}.")
            self._logger.warning("Execução terminada com código %s", exit_code)

    def _append_output(self, text: str) -> None:
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self._logger.debug("Output acumulado: %s", text.rstrip())

    def _clear_output(self) -> None:
        self.output.delete("1.0", tk.END)

    def _copy_all_output(self) -> None:
        content = self.output.get("1.0", "end-1c")
        toplevel = self.winfo_toplevel()
        toplevel.clipboard_clear()
        if content:
            toplevel.clipboard_append(content)
            self.status_var.set("Log copiado para a área de transferência.")
        else:
            self.status_var.set("Não existe conteúdo para copiar.")


class ValidationTab(OperationTab):
    """Executa a validação completa do ficheiro SAF-T."""

    def __init__(self, master: tk.Misc, folders: DefaultFolderManager) -> None:
        super().__init__(master)
        self._folders = folders

        self.xml_var = tk.StringVar()
        self.xsd_var = tk.StringVar()
        self.destination_label = ttk.Label(self, wraplength=700, justify=tk.LEFT)

        form = ttk.Frame(self)
        form.grid_columnconfigure(1, weight=1)

        xml_entry = ttk.Entry(form, textvariable=self.xml_var)
        xml_button = ttk.Button(form, text="Escolher ficheiro…", command=self._select_xml)
        self._add_form_row(form, 0, "Ficheiro SAF-T:", xml_entry, xml_button)

        xsd_entry = ttk.Entry(form, textvariable=self.xsd_var)
        xsd_button = ttk.Button(form, text="Escolher XSD…", command=self._select_xsd)
        self._add_form_row(form, 1, "Ficheiro XSD (opcional):", xsd_entry, xsd_button)

        self._xsd_hint = ttk.Label(
            self,
            text="",
            wraplength=700,
            justify=tk.LEFT,
            font=("Segoe UI", 9, "italic"),
        )

        run_button = ttk.Button(self, text="Executar validação")
        self.register_run_button(run_button)

        form.pack(fill="x", pady=(0, 12))
        self._xsd_hint.pack(anchor="w", pady=(0, 4))
        run_button.pack(anchor="w")
        self.destination_label.pack(anchor="w", pady=(12, 0))
        self.status_label.pack(anchor="w", pady=(12, 0))
        self.output_container.pack(fill="both", expand=True, pady=(12, 0))

        self._folders.subscribe(self._on_folder_changed)
        self._refresh_default_xsd_hint()
        self._update_destination_label()

    def _add_form_row(
        self,
        form: ttk.Frame,
        row: int,
        label: str,
        entry: ttk.Entry,
        button: ttk.Button,
    ) -> None:
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
        entry.grid(row=row, column=1, sticky="we", pady=4)
        button.grid(row=row, column=2, sticky="w", pady=4)

    def _select_xml(self) -> None:
        base_dir = self._folders.get_folder(DefaultFolderManager.FOLDER_ORIGIN)
        path = filedialog.askopenfilename(
            title="Selecionar ficheiro SAF-T",
            initialdir=str(base_dir),
            filetypes=[("Ficheiros SAF-T", "*.xml"), ("Todos os ficheiros", "*.*")],
        )
        if path:
            self.xml_var.set(path)
            self._logger.info("Ficheiro SAF-T selecionado: %s", path)

    def _select_xsd(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar ficheiro XSD",
            initialdir=str(configured_default_xsd_directory()),
            filetypes=[("Ficheiros XSD", "*.xsd"), ("Todos os ficheiros", "*.*")],
        )
        if path:
            self.xsd_var.set(path)
            self._logger.info("Ficheiro XSD selecionado: %s", path)

    def build_command(self) -> tuple[list[str], Path | None]:
        xml_path = self._require_existing_path(self.xml_var.get(), "ficheiro SAF-T")
        arguments = [str(VALIDATOR_SCRIPT), str(xml_path)]

        xsd_text = self.xsd_var.get().strip()
        self._refresh_default_xsd_hint()

        if xsd_text:
            xsd_path = self._require_existing_path(xsd_text, "ficheiro XSD")
            arguments.extend(["--xsd", str(xsd_path)])
        else:
            configured_xsd = configured_default_xsd_path(fallback_to_builtin=False)
            if configured_xsd is not None and not configured_xsd.exists():
                raise UserInputError(
                    "O ficheiro XSD por defeito configurado não foi encontrado em "
                    f"'{configured_xsd}'. Atualize a configuração ou selecione um ficheiro."
                )
            fallback_xsd = configured_default_xsd_path()
            if fallback_xsd:
                arguments.extend(["--xsd", str(fallback_xsd)])
                self._logger.info("Ficheiro XSD por defeito aplicado: %s", fallback_xsd)

        destination = self._folders.get_folder(DefaultFolderManager.FOLDER_VALIDATION)
        self._logger.info(
            "Validação preparada para %s com destino %s", xml_path, destination
        )
        return arguments, destination

    def _refresh_default_xsd_hint(self) -> None:
        default_xsd = configured_default_xsd_path()
        if default_xsd:
            self._xsd_hint.configure(
                text=f"Caso não seleccione um ficheiro, será usado: {default_xsd}",
            )
        else:
            self._xsd_hint.configure(text="")

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
        self.destination_label.configure(
            text=(
                "Os resultados (ficheiro Excel de log) são gravados em: "
                f"{destination}"
            )
        )

    def _on_folder_changed(self, key: str, _path: Path) -> None:
        if key == DefaultFolderManager.FOLDER_VALIDATION:
            self._update_destination_label()


class AutoFixTab(OperationTab):
    """Base para *tabs* de execução dos scripts de auto-correcção."""

    def __init__(
        self,
        master: tk.Misc,
        script_path: Path,
        label: str,
        folders: DefaultFolderManager,
        destination_key: str,
    ) -> None:
        super().__init__(master)
        self._script_path = script_path
        self._folders = folders
        self._destination_key = destination_key

        self.xml_var = tk.StringVar()
        self.customer_excel_var = tk.StringVar()
        self.destination_label = ttk.Label(self, wraplength=700, justify=tk.LEFT)

        form = ttk.Frame(self)
        form.grid_columnconfigure(1, weight=1)

        xml_entry = ttk.Entry(form, textvariable=self.xml_var)
        xml_button = ttk.Button(form, text="Escolher ficheiro…", command=self._select_xml)
        self._add_form_row(form, 0, "Ficheiro SAF-T:", xml_entry, xml_button)

        customer_entry = ttk.Entry(form, textvariable=self.customer_excel_var)
        customer_button = ttk.Button(
            form, text="Escolher ficheiro…", command=self._select_customer_excel
        )
        self._add_form_row(
            form,
            1,
            "Ficheiro Excel de clientes (opcional):",
            customer_entry,
            customer_button,
        )

        description = ttk.Label(
            self,
            text=(
                "O ficheiro selecionado é processado diretamente. Os resultados "
                "(novas versões do XML e log em Excel) são gravados na pasta de "
                "destino configurada."
            ),
            wraplength=700,
            justify=tk.LEFT,
        )

        run_button = ttk.Button(self, text=label)
        self.register_run_button(run_button)

        form.pack(fill="x", pady=(0, 12))
        description.pack(anchor="w")
        run_button.pack(anchor="w", pady=(12, 0))
        self.destination_label.pack(anchor="w", pady=(12, 0))
        self.status_label.pack(anchor="w", pady=(12, 0))
        self.output_container.pack(fill="both", expand=True, pady=(12, 0))

        self._folders.subscribe(self._on_folder_changed)
        self._update_destination_label()

    def _add_form_row(
        self,
        form: ttk.Frame,
        row: int,
        label: str,
        entry: ttk.Entry,
        button: ttk.Button,
    ) -> None:
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
        entry.grid(row=row, column=1, sticky="we", pady=4)
        button.grid(row=row, column=2, sticky="w", pady=4)

    def _select_xml(self) -> None:
        base_dir = self._folders.get_folder(DefaultFolderManager.FOLDER_ORIGIN)
        path = filedialog.askopenfilename(
            title="Selecionar ficheiro SAF-T",
            initialdir=str(base_dir),
            filetypes=[("Ficheiros SAF-T", "*.xml"), ("Todos os ficheiros", "*.*")],
        )
        if path:
            self.xml_var.set(path)
            self._logger.info("Ficheiro SAF-T selecionado para auto-fix: %s", path)

    def _select_customer_excel(self) -> None:
        base_dir = self._folders.get_folder(DefaultFolderManager.FOLDER_CLIENT_CERT_SOURCE)
        path = filedialog.askopenfilename(
            title="Selecionar ficheiro Excel de clientes",
            initialdir=str(base_dir),
            filetypes=[
                ("Ficheiros Excel", "*.xlsx"),
                ("Ficheiros Excel (antigos)", "*.xls"),
                ("Todos os ficheiros", "*.*"),
            ],
        )
        if path:
            self.customer_excel_var.set(path)
            self._logger.info("Ficheiro Excel de clientes selecionado: %s", path)

    def build_command(self) -> tuple[list[str], Path | None]:
        xml_path = self._require_existing_path(self.xml_var.get())
        customer_excel = self._optional_customer_excel()
        destination_dir = self._folders.get_folder(self._destination_key)
        destination_dir.mkdir(parents=True, exist_ok=True)

        command = [
            str(self._script_path),
            str(xml_path),
            "--output-dir",
            str(destination_dir),
        ]

        self._logger.info(
            "Execução preparada para %s com destino %s",
            xml_path,
            destination_dir,
        )
        if customer_excel:
            self._logger.info(
                "Ficheiro Excel de clientes configurado para auto-fix: %s",
                customer_excel,
            )
        return command, destination_dir

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
        self.destination_label.configure(
            text="Os resultados (XML e log) são gravados em: " f"{destination_dir}"
        )

    def env_overrides(self) -> Mapping[str, str | None] | None:
        customer_excel = self._optional_customer_excel(raise_on_invalid=False)
        if customer_excel is None:
            return {CUSTOMER_EXCEL_ENV: None}
        return {CUSTOMER_EXCEL_ENV: str(customer_excel)}

    def _on_folder_changed(self, key: str, _path: Path) -> None:
        if key in (self._destination_key, DefaultFolderManager.FOLDER_ORIGIN):
            self._update_destination_label()

    def _optional_customer_excel(self, *, raise_on_invalid: bool = True) -> Path | None:
        text = self.customer_excel_var.get().strip()
        if not text:
            return None
        path = Path(text).expanduser()
        if raise_on_invalid and not path.exists():
            raise UserInputError(f"O ficheiro Excel '{path}' não foi encontrado.")
        if raise_on_invalid and path.is_dir():
            raise UserInputError("Indique um ficheiro Excel válido, não uma pasta.")
        return path


class ReportTab(OperationTab):
    """Gera relatórios de totais contabilísticos em Excel."""

    def __init__(self, master: tk.Misc, folders: DefaultFolderManager) -> None:
        super().__init__(master)
        self._folders = folders
        self._default_output_dir = self._folders.get_folder(
            DefaultFolderManager.FOLDER_REPORT_DESTINATION
        )

        self._saft_var = tk.StringVar()
        self._output_destination_var = tk.StringVar()

        form = ttk.Frame(self)
        form.grid_columnconfigure(1, weight=1)

        saft_entry = ttk.Entry(form, textvariable=self._saft_var)
        saft_button = ttk.Button(form, text="Escolher ficheiro…", command=self._select_saft)
        self._add_form_row(form, 0, "Ficheiro SAF-T:", saft_entry, saft_button)

        ttk.Label(form, text="Relatório Excel:").grid(
            row=1, column=0, sticky="nw", pady=4, padx=(0, 8)
        )
        output_value = ttk.Label(
            form,
            textvariable=self._output_destination_var,
            relief="solid",
            anchor="w",
            padding=(6, 4),
        )
        output_value.grid(row=1, column=1, columnspan=2, sticky="we", pady=4)

        description = ttk.Label(
            self,
            text=(
                "Gera um ficheiro Excel com totais por tipo de documento e uma "
                "listagem separada de documentos não contabilísticos."
            ),
            wraplength=700,
            justify=tk.LEFT,
        )

        self._output_hint = ttk.Label(
            self,
            text="",
            wraplength=700,
            justify=tk.LEFT,
            font=("Segoe UI", 9, "italic"),
        )

        run_button = ttk.Button(self, text="Gerar relatório de totais")
        self.register_run_button(run_button)

        form.pack(fill="x", pady=(0, 12))
        description.pack(anchor="w")
        self._output_hint.pack(anchor="w", pady=(4, 0))
        run_button.pack(anchor="w", pady=(12, 0))
        self.status_label.pack(anchor="w", pady=(12, 0))
        self.output_container.pack(fill="both", expand=True, pady=(12, 0))

        self._folders.subscribe(self._on_folder_changed)
        self._update_output_destination()
        self._refresh_output_hint()

    def _add_form_row(
        self,
        form: ttk.Frame,
        row: int,
        label: str,
        entry: ttk.Entry,
        button: ttk.Button,
    ) -> None:
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
        entry.grid(row=row, column=1, sticky="we", pady=4)
        button.grid(row=row, column=2, sticky="w", pady=4)

    def _select_saft(self) -> None:
        base_dir = self._folders.get_folder(DefaultFolderManager.FOLDER_ORIGIN)
        path = filedialog.askopenfilename(
            title="Selecionar ficheiro SAF-T",
            initialdir=str(base_dir),
            filetypes=[("Ficheiros SAF-T", "*.xml"), ("Todos os ficheiros", "*.*")],
        )
        if path:
            self._saft_var.set(path)
            self._logger.info("Ficheiro SAF-T selecionado para relatório: %s", path)
            self._update_output_destination()

    def build_command(self) -> tuple[list[str], Path | None]:
        saft_path = self._require_existing_saft(self._saft_var.get())
        output_path = self._suggested_output_path()
        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        command = [str(REPORT_SCRIPT), str(saft_path)]
        self._logger.info(
            "Relatório preparado para %s com destino %s",
            saft_path,
            output_path,
        )
        return command, output_dir

    def _update_output_destination(self) -> None:
        suggestion = self._suggested_output_path()
        self._output_destination_var.set(str(suggestion))

    def _refresh_output_hint(self) -> None:
        suggestion = self._suggested_output_path()
        self._output_hint.configure(
            text=(
                "O relatório é gerado automaticamente no destino indicado "
                f"acima: {suggestion}"
            )
        )

    def _suggested_output_path(self) -> Path:
        saft_text = self._saft_var.get().strip()
        saft_path: Path | None = None
        if saft_text:
            try:
                saft_path = Path(saft_text).expanduser()
            except Exception:
                saft_path = Path(saft_text)
        return default_report_destination(saft_path, base_dir=self._default_output_dir)

    def _on_folder_changed(self, key: str, path: Path) -> None:
        if key == DefaultFolderManager.FOLDER_REPORT_DESTINATION:
            self._default_output_dir = path
            self._refresh_output_hint()
            self._update_output_destination()

    @staticmethod
    def _require_existing_saft(value: str) -> Path:
        text = value.strip()
        if not text:
            raise UserInputError("Selecione um ficheiro SAF-T.")
        path = Path(text).expanduser()
        if not path.exists():
            raise UserInputError(f"O ficheiro SAF-T '{path}' não foi encontrado.")
        if path.is_dir():
            raise UserInputError("Indique um ficheiro SAF-T válido, não uma pasta.")
        return path

class ClientCertificationTab(OperationTab):
    """Executa a certificação de clientes baseada no Excel fornecido."""

    def __init__(self, master: tk.Misc, folders: DefaultFolderManager) -> None:
        super().__init__(master)
        self._folders = folders
        self._default_output_dir = self._folders.get_folder(
            DefaultFolderManager.FOLDER_CLIENT_CERT_DESTINATION
        )

        self._input_var = tk.StringVar()
        self._output_dir_var = tk.StringVar(value=str(self._default_output_dir))
        self._destination_label = ttk.Label(self, wraplength=700, justify=tk.LEFT)

        form = ttk.Frame(self)
        form.grid_columnconfigure(1, weight=1)

        input_entry = ttk.Entry(form, textvariable=self._input_var)
        input_button = ttk.Button(
            form, text="Escolher ficheiro…", command=self._select_input
        )
        self._add_form_row(
            form,
            0,
            "Ficheiro Excel de clientes:",
            input_entry,
            input_button,
        )

        output_entry = ttk.Entry(form, textvariable=self._output_dir_var)
        output_button = ttk.Button(
            form, text="Escolher pasta…", command=self._select_output_dir
        )
        self._add_form_row(
            form,
            1,
            "Destino do ficheiro corrigido:",
            output_entry,
            output_button,
        )

        description = ttk.Label(
            self,
            text=(
                "Processa o ficheiro Excel de clientes recorrendo aos dados da AGT e "
                "gera uma versão corrigida na pasta de destino indicada."
            ),
            wraplength=700,
            justify=tk.LEFT,
        )

        run_button = ttk.Button(self, text="Certificar clientes")
        self.register_run_button(run_button)

        form.pack(fill="x", pady=(0, 12))
        description.pack(anchor="w")
        run_button.pack(anchor="w", pady=(12, 0))
        self._destination_label.pack(anchor="w", pady=(12, 0))
        self.status_label.pack(anchor="w", pady=(12, 0))
        self.output_container.pack(fill="both", expand=True, pady=(12, 0))

        self._folders.subscribe(self._on_folder_changed)
        self._update_input_placeholder()
        self._update_destination_label(self._default_output_dir)

    def _add_form_row(
        self,
        form: ttk.Frame,
        row: int,
        label: str,
        entry: ttk.Entry,
        button: ttk.Button,
    ) -> None:
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=4, padx=(0, 8))
        entry.grid(row=row, column=1, sticky="we", pady=4)
        button.grid(row=row, column=2, sticky="w", pady=4)

    def _select_input(self) -> None:
        base_dir = self._folders.get_folder(DefaultFolderManager.FOLDER_CLIENT_CERT_SOURCE)
        path = filedialog.askopenfilename(
            title="Selecionar ficheiro Excel de clientes",
            initialdir=str(base_dir),
            filetypes=[("Ficheiros Excel", "*.xlsx"), ("Todos os ficheiros", "*.*")],
            parent=self.winfo_toplevel(),
        )
        if path:
            self._input_var.set(path)
            self._logger.info("Ficheiro Excel selecionado: %s", path)

    def _select_output_dir(self) -> None:
        current_text = self._output_dir_var.get().strip()
        current = Path(current_text).expanduser() if current_text else self._default_output_dir
        path = filedialog.askdirectory(
            title="Selecionar pasta de destino",
            initialdir=str(current),
        )
        if path:
            self._output_dir_var.set(path)
            self._logger.info("Pasta de destino seleccionada: %s", path)

    def build_command(self) -> tuple[list[str], Path | None]:
        input_path = self._require_existing_excel(self._input_var.get())
        output_dir_text = self._output_dir_var.get().strip()
        if output_dir_text:
            output_dir = Path(output_dir_text).expanduser()
        else:
            output_dir = self._folders.get_folder(
                DefaultFolderManager.FOLDER_CLIENT_CERT_DESTINATION
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = input_path.suffix or ".xlsx"
        output_file = output_dir / f"{input_path.stem}_corrigido{suffix}"

        command = [
            str(CLIENT_CERT_SCRIPT),
            "--input",
            str(input_path),
            "--output",
            str(output_file),
        ]

        self._logger.info(
            "Certificação preparada para %s com destino %s",
            input_path,
            output_file,
        )
        return command, output_dir

    @staticmethod
    def _require_existing_excel(value: str) -> Path:
        text = value.strip()
        if not text:
            raise UserInputError("Selecione um ficheiro Excel de clientes.")
        path = Path(text).expanduser()
        if not path.exists():
            raise UserInputError(f"O ficheiro '{path}' não foi encontrado.")
        if path.is_dir():
            raise UserInputError("Indique um ficheiro Excel válido, não uma pasta.")
        return path

    def _update_input_placeholder(self) -> None:
        source_dir = self._folders.get_folder(
            DefaultFolderManager.FOLDER_CLIENT_CERT_SOURCE
        )
        if not self._input_var.get():
            self._input_var.set(str(source_dir))

    def _update_destination_label(self, directory: Path | None = None) -> None:
        if directory is None:
            directory = self._folders.get_folder(
                DefaultFolderManager.FOLDER_CLIENT_CERT_DESTINATION
            )
        self._destination_label.configure(
            text="O ficheiro corrigido é gravado em: " f"{directory}"
        )

    def _on_folder_changed(self, key: str, new_path: Path) -> None:
        if key == DefaultFolderManager.FOLDER_CLIENT_CERT_SOURCE:
            self._update_input_placeholder()
        if key == DefaultFolderManager.FOLDER_CLIENT_CERT_DESTINATION:
            current_text = self._output_dir_var.get().strip()
            current_path: Path | None = None
            if current_text:
                try:
                    current_path = Path(current_text).expanduser().resolve()
                except FileNotFoundError:
                    current_path = Path(current_text).expanduser()
            if current_path is not None and current_path == self._default_output_dir:
                self._output_dir_var.set(str(new_path))
            elif not current_text:
                self._output_dir_var.set(str(new_path))
            self._default_output_dir = new_path.resolve()
            self._update_destination_label(new_path)


class RuleUpdateTab(OperationTab):
    """Interface para o utilitário de registo de actualizações de regras."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.note_var = tk.StringVar()
        self.tag_var = tk.StringVar()
        self.schema_target_var = tk.StringVar()
        self.xsd_var = tk.StringVar()
        self.rules_list = tk.Listbox(self, selectmode=tk.EXTENDED, height=6)

        form = ttk.Frame(self)
        form.grid_columnconfigure(1, weight=1)

        ttk.Label(form, text="Nota:").grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(form, textvariable=self.note_var).grid(
            row=0, column=1, sticky="we", pady=4
        )

        ttk.Label(form, text="Etiqueta (opcional):").grid(
            row=1, column=0, sticky="w", pady=4, padx=(0, 8)
        )
        ttk.Entry(form, textvariable=self.tag_var).grid(
            row=1, column=1, sticky="we", pady=4
        )

        ttk.Label(form, text="Destino schema (opcional):").grid(
            row=2, column=0, sticky="nw", pady=4, padx=(0, 8)
        )
        ttk.Label(
            form,
            text="Ex.: SAFTAO1.01_01.xsd ou subpastas dentro de 'schemas/'.",
            wraplength=360,
        ).grid(row=2, column=1, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.schema_target_var).grid(
            row=3, column=1, sticky="we", pady=4
        )

        xsd_entry = ttk.Entry(form, textvariable=self.xsd_var)
        xsd_button = ttk.Button(form, text="Escolher XSD…", command=self._select_xsd)
        ttk.Label(form, text="Ficheiro XSD (opcional):").grid(
            row=4, column=0, sticky="w", pady=4, padx=(0, 8)
        )
        xsd_entry.grid(row=4, column=1, sticky="we", pady=4)
        xsd_button.grid(row=4, column=2, sticky="w", pady=4)

        rules_box = ttk.LabelFrame(self, text="Ficheiros de regras")
        rules_box.pack(fill="both", expand=False, pady=(12, 0))
        rules_box.grid_columnconfigure(0, weight=1)

        self.rules_list.pack(in_=rules_box, fill="both", expand=True, padx=8, pady=8)

        button_row = ttk.Frame(rules_box)
        button_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(
            button_row,
            text="Adicionar ficheiros de regras…",
            command=self._add_rule_files,
        ).pack(side=tk.LEFT)
        ttk.Button(
            button_row,
            text="Remover selecionados",
            command=self._remove_selected_rules,
        ).pack(side=tk.LEFT, padx=(8, 0))

        run_button = ttk.Button(self, text="Registar actualização")
        self.register_run_button(run_button)

        form.pack(fill="x", pady=(0, 12))
        run_button.pack(anchor="w")
        self.status_label.pack(anchor="w", pady=(12, 0))
        self.output_container.pack(fill="both", expand=True, pady=(12, 0))

    def _select_xsd(self) -> None:
        path = filedialog.askopenfilename(
            title="Selecionar ficheiro XSD",
            initialdir=str(configured_default_xsd_directory()),
            filetypes=[("Ficheiros XSD", "*.xsd"), ("Todos os ficheiros", "*.*")],
        )
        if path:
            self.xsd_var.set(path)

    def _add_rule_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Selecionar ficheiros de regras",
            initialdir=str(Path.home()),
            filetypes=[("Todos os ficheiros", "*.*")],
        )
        existing = {self.rules_list.get(idx) for idx in range(self.rules_list.size())}
        for path in paths:
            if path and path not in existing:
                self.rules_list.insert(tk.END, path)

    def _remove_selected_rules(self) -> None:
        for index in reversed(self.rules_list.curselection()):
            self.rules_list.delete(index)

    def build_command(self) -> tuple[list[str], Path | None]:
        note = self.note_var.get().strip()
        if not note:
            raise UserInputError("Indique uma nota descritiva para a actualização.")

        arguments: list[str] = ["-m", "saftao.rules_updates", "--note", note]
        self._logger.info("Preparar registo de regras: nota '%s'", note)

        tag = self.tag_var.get().strip()
        if tag:
            arguments.extend(["--tag", tag])

        schema_target = self.schema_target_var.get().strip()
        if schema_target:
            arguments.extend(["--schema-target", schema_target])

        xsd_text = self.xsd_var.get().strip()
        if xsd_text:
            xsd_path = self._require_existing(xsd_text, "ficheiro XSD")
            arguments.extend(["--xsd", str(xsd_path)])

        rules = [self.rules_list.get(i) for i in range(self.rules_list.size())]
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


class DefaultFoldersFrame(ttk.Frame):
    """Permite configurar as pastas por defeito utilizadas pelas operações."""

    def __init__(self, master: tk.Misc, folders: DefaultFolderManager) -> None:
        super().__init__(master)
        self._folders = folders
        self._edits: dict[str, tk.StringVar] = {}
        self._logger = LOGGER.getChild("DefaultFolders")
        self._xsd_var = tk.StringVar()
        if DEFAULT_XSD.exists():
            self._xsd_var.set(str(DEFAULT_XSD))

        description = ttk.Label(
            self,
            text=(
                "Configure abaixo as pastas por defeito utilizadas para abrir e "
                "guardar ficheiros. As pastas são criadas automaticamente caso "
                "não existam."
            ),
            wraplength=760,
            justify=tk.LEFT,
        )

        form = ttk.Frame(self)
        form.grid_columnconfigure(1, weight=1)

        row = 0
        for key in self._folders.keys():
            var = tk.StringVar(value=str(self._folders.get_folder(key)))
            self._edits[key] = var
            browse_button = ttk.Button(
                form, text="Escolher pasta…", command=partial(self._select_folder, key)
            )
            ttk.Label(form, text=self._folders.label_for(key) + ":").grid(
                row=row, column=0, sticky="w", pady=4, padx=(0, 8)
            )
            ttk.Entry(form, textvariable=var).grid(
                row=row, column=1, sticky="we", pady=4
            )
            browse_button.grid(row=row, column=2, sticky="w", pady=4)
            row += 1

        xsd_button = ttk.Button(form, text="Escolher ficheiro…", command=self._select_xsd)
        ttk.Label(form, text="Ficheiro XSD por defeito:").grid(
            row=row, column=0, sticky="w", pady=4, padx=(0, 8)
        )
        ttk.Entry(form, textvariable=self._xsd_var).grid(
            row=row, column=1, sticky="we", pady=4
        )
        xsd_button.grid(row=row, column=2, sticky="w", pady=4)

        save_button = ttk.Button(self, text="Guardar alterações", command=self._save_changes)
        reset_button = ttk.Button(
            self, text="Repor valores por defeito", command=self._reset_defaults
        )

        button_row = ttk.Frame(self)
        button_row.pack(fill="x", pady=(12, 0))
        save_button.pack(in_=button_row, side=tk.LEFT)
        reset_button.pack(in_=button_row, side=tk.LEFT, padx=(8, 0))

        description.pack(anchor="w", pady=(0, 12))
        form.pack(fill="x")

        self._folders.subscribe(self._on_folder_changed)
        self._reload_from_manager()

    def _select_folder(self, key: str) -> None:
        current_text = self._edits[key].get().strip()
        current = Path(current_text).expanduser() if current_text else Path.home()
        base_dir = current if current.exists() else Path.home()
        path = filedialog.askdirectory(
            title="Selecionar pasta",
            initialdir=str(base_dir),
        )
        if path:
            self._edits[key].set(path)
            self._logger.info("Pasta seleccionada para '%s': %s", key, path)

    def _select_xsd(self) -> None:
        base_dir = configured_default_xsd_directory()
        path = filedialog.askopenfilename(
            title="Selecionar ficheiro XSD",
            initialdir=str(base_dir),
            filetypes=[("Ficheiros XSD", "*.xsd"), ("Todos os ficheiros", "*.*")],
        )
        if path:
            self._xsd_var.set(path)
            self._logger.info("Ficheiro XSD por defeito seleccionado: %s", path)

    def _save_changes(self) -> None:
        new_values: dict[str, Path] = {}
        for key, var in self._edits.items():
            text = var.get().strip()
            if not text:
                messagebox.showwarning(
                    "Pasta inválida",
                    "Indique um caminho válido para todas as pastas.",
                )
                self._logger.warning(
                    "Tentativa de guardar com pasta vazia em '%s'", key
                )
                return
            new_values[key] = Path(text).expanduser()

        xsd_text = self._xsd_var.get().strip()
        xsd_path: Path | None
        if xsd_text:
            xsd_path = Path(xsd_text).expanduser()
            if not xsd_path.exists():
                messagebox.showwarning(
                    "Ficheiro XSD inválido",
                    "O ficheiro XSD indicado não existe. Corrija o caminho ou deixe o campo vazio para usar o padrão.",
                )
                self._logger.warning(
                    "Tentativa de configurar XSD por defeito inexistente: %s",
                    xsd_path,
                )
                return
        else:
            xsd_path = None

        try:
            for key, path in new_values.items():
                self._folders.set_folder(key, path)
        except OSError as exc:  # pragma: no cover - depende do FS
            messagebox.showerror(
                "Erro ao guardar",
                f"Não foi possível criar uma das pastas indicadas: {exc}",
            )
            self._logger.exception("Falha ao actualizar pastas por defeito.")
            return

        store_configured_default_xsd(xsd_path)
        messagebox.showinfo("Configuração actualizada", "Alterações guardadas com sucesso.")
        self._logger.info("Pastas por defeito actualizadas.")

    def _reset_defaults(self) -> None:
        if not messagebox.askyesno(
            "Repor valores",
            "Pretende repor os valores por defeito?",
        ):
            return
        self._folders.reset_to_defaults()
        store_configured_default_xsd(DEFAULT_XSD if DEFAULT_XSD.exists() else None)
        self._reload_from_manager()
        self._logger.info("Pastas por defeito repostas.")

    def _reload_from_manager(self) -> None:
        for key, var in self._edits.items():
            var.set(str(self._folders.get_folder(key)))
        default_xsd = configured_default_xsd_path()
        self._xsd_var.set(str(default_xsd) if default_xsd else "")

    def _on_folder_changed(self, key: str, path: Path) -> None:
        if key in self._edits:
            self._edits[key].set(str(path))


class MainApplication:
    """Janela principal da aplicação Tkinter."""

    def __init__(self) -> None:
        LOGGER.info("Aplicação GUI iniciada.")
        self.root = tk.Tk()
        self.root.title("Ferramentas SAF-T (AO)")
        self.root.geometry("1100x760")
        self.root.configure(bg="#12131b")
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.96)
        self.root.bind("<Escape>", lambda _event: self.close())
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self._background_image: tk.PhotoImage | None = None
        if BACKGROUND_IMAGE.exists():
            try:
                self._background_image = tk.PhotoImage(file=str(BACKGROUND_IMAGE))
            except tk.TclError as exc:  # pragma: no cover - depende do ambiente
                LOGGER.warning("Falha ao carregar imagem de fundo: %s", exc)
            else:
                bg_label = tk.Label(self.root, image=self._background_image, borderwidth=0)
                bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.container = tk.Frame(self.root, bg="#1c1f2a", bd=0, highlightthickness=0)
        self.container.pack(fill="both", expand=True, padx=24, pady=24)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:  # pragma: no cover - tema não disponível
            pass
        style.configure("TFrame", background="#1c1f2a")
        style.configure("TLabel", background="#1c1f2a", foreground="#f0f0f0")
        style.configure("TButton", padding=6)
        style.configure("TNotebook", background="#1c1f2a")
        style.configure("TNotebook.Tab", padding=(12, 8))

        self._build_title_bar()

        content = ttk.Frame(self.container)
        content.pack(fill="both", expand=True, pady=(12, 0))

        self.folders = DefaultFolderManager()
        self.tabs: list[OperationTab | DefaultFoldersFrame] = []

        notebook = ttk.Notebook(content)
        notebook.pack(fill="both", expand=True)

        validation_tab = ValidationTab(notebook, self.folders)
        notebook.add(validation_tab, text="Validação")
        self.tabs.append(validation_tab)

        fix_standard_tab = AutoFixTab(
            notebook,
            AUTOFIX_SOFT_SCRIPT,
            "Executar Fix Precisão Standard",
            self.folders,
            DefaultFolderManager.FOLDER_FIX_STANDARD,
        )
        notebook.add(fix_standard_tab, text="Fix Precisão Standard")
        self.tabs.append(fix_standard_tab)

        fix_high_tab = AutoFixTab(
            notebook,
            AUTOFIX_HARD_SCRIPT,
            "Executar Fix Precisão Alta",
            self.folders,
            DefaultFolderManager.FOLDER_FIX_HIGH,
        )
        notebook.add(fix_high_tab, text="Fix Precisão Alta")
        self.tabs.append(fix_high_tab)

        report_tab = ReportTab(notebook, self.folders)
        notebook.add(report_tab, text="Relatório de Totais")
        self.tabs.append(report_tab)

        client_tab = ClientCertificationTab(notebook, self.folders)
        notebook.add(client_tab, text="Certifica Clientes")
        self.tabs.append(client_tab)

        rules_tab = RuleUpdateTab(notebook)
        notebook.add(rules_tab, text="Actualizações de Regras")
        self.tabs.append(rules_tab)

        folders_tab = DefaultFoldersFrame(notebook, self.folders)
        notebook.add(folders_tab, text="Pastas por Defeito")
        self.tabs.append(folders_tab)  # type: ignore[arg-type]

        LOGGER.info("Janela principal pronta.")

    def _build_title_bar(self) -> None:
        title_bar = tk.Frame(self.container, bg="#0f111a", height=36)
        title_bar.pack(fill="x")

        title_label = tk.Label(
            title_bar,
            text="Ferramentas SAF-T (AO)",
            bg="#0f111a",
            fg="#f5f5f5",
            font=("Segoe UI", 12, "bold"),
        )
        title_label.pack(side=tk.LEFT, padx=12)

        buttons = tk.Frame(title_bar, bg="#0f111a")
        buttons.pack(side=tk.RIGHT, padx=8)

        def _make_button(text: str, command: Callable[[], None]) -> tk.Button:
            btn = tk.Button(
                buttons,
                text=text,
                command=command,
                bd=0,
                width=4,
                background="#0f111a",
                foreground="#f5f5f5",
                activebackground="#1f2233",
                activeforeground="#ffffff",
                highlightthickness=0,
            )
            return btn

        _make_button("—", self.root.iconify).pack(side=tk.LEFT)
        _make_button("✕", self.close).pack(side=tk.LEFT, padx=(8, 0))

        def start_move(event: tk.Event[tk.Misc]) -> None:  # type: ignore[type-arg]
            self._drag_start = (event.x_root, event.y_root)
            self._window_start = (self.root.winfo_x(), self.root.winfo_y())

        def on_move(event: tk.Event[tk.Misc]) -> None:  # type: ignore[type-arg]
            dx = event.x_root - self._drag_start[0]
            dy = event.y_root - self._drag_start[1]
            new_x = self._window_start[0] + dx
            new_y = self._window_start[1] + dy
            self.root.geometry(f"+{new_x}+{new_y}")

        for widget in (title_bar, title_label):
            widget.bind("<ButtonPress-1>", start_move)
            widget.bind("<B1-Motion>", on_move)

    def run(self) -> None:
        LOGGER.info("A entrar no loop principal do Tkinter.")
        self.root.mainloop()

    def close(self) -> None:
        LOGGER.info("Pedido para fechar a aplicação.")
        for tab in self.tabs:
            if isinstance(tab, OperationTab):
                tab.cleanup()
        self.root.destroy()


def main() -> int:
    app = MainApplication()
    app.run()
    LOGGER.info("Aplicação terminada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
