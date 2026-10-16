import ctypes
import os
from pathlib import Path

from rich.text import Text
from textual import on
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Checkbox, DirectoryTree, Label, Select, Static

from ..i18n import tr
from .dialogs import FormDialog
from .safe_text import SafeInput, safe_text


def drive_roots(current: Path):
    roots = []
    if os.name == "nt":
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        roots = [f"{chr(65 + i)}:\\" for i in range(26) if mask & (1 << i)]
    else:
        roots = ["/"]
    if current.anchor and current.anchor not in roots:
        roots.append(current.anchor)
    return roots


class SpreadsheetTree(DirectoryTree):
    def filter_paths(self, paths):
        suffix = getattr(self.screen, "file_extension", "all")
        return [p for p in paths if p.is_dir() or suffix == "all" or p.suffix.lower() == suffix]


class FileDialog(FormDialog):
    DEFAULT_CSS = """
    FileDialog > Vertical { width: 90; max-width: 96%; height: 90%; max-height: 90%; }
    FileDialog VerticalScroll { height: 1fr; max-height: 100%; }
    FileDialog #file-tree { height: 9; min-height: 5; border: solid $panel; }
    FileDialog #drive { width: 1fr; }
    FileDialog #folder-up, FileDialog #folder-home, FileDialog #folder-go, FileDialog #folder-root { width: auto; min-width: 8; }
    FileDialog #folder-path { width: 1fr; }
    FileDialog Horizontal { height: 3; }
    """

    def __init__(self, title, submit, folder, path="", language="ko", saving=False, notice=""):
        super().__init__(title, [], submit, language, notice)
        self.folder = Path(folder).expanduser().resolve()
        while not self.folder.is_dir() and self.folder.parent != self.folder:
            self.folder = self.folder.parent
        self.initial_path = str(path)
        self.saving = saving
        self.allowed_extensions = (
            [".texel"] if title == "backup" else [".texel", ".xlsx", ".csv", ".tsv"]
        )
        self.file_extension = (
            Path(path).suffix.lower()
            if saving and Path(path).suffix.lower() in {".texel", ".xlsx", ".csv", ".tsv"}
            else ".xlsx"
            if saving
            else "all"
        )

    def compose(self):
        with Vertical():
            yield Label(tr(self.title_text, self.language), classes="form-title")
            with VerticalScroll():
                with Horizontal():
                    roots = drive_roots(self.folder)
                    yield Select(
                        [(r, r) for r in roots],
                        value=self.folder.anchor or roots[0],
                        allow_blank=False,
                        id="drive",
                    )
                    yield Button(tr("folder_up", self.language), id="folder-up")
                    yield Button(tr("folder_home", self.language), id="folder-home")
                    yield Button(tr("folder_root", self.language), id="folder-root")
                with Horizontal():
                    yield SafeInput(str(self.folder), id="folder-path", select_on_focus=True)
                    yield Button(tr("folder_go", self.language), id="folder-go")
                yield SpreadsheetTree(self.folder, id="file-tree")
                yield Label(tr("path", self.language))
                yield SafeInput(self.initial_path, id="field-path")
                choices = (
                    self.allowed_extensions
                    if self.saving
                    else ["all", ".texel", ".xlsx", ".csv", ".tsv", ".xls", ".gsheet"]
                )
                yield Label(tr("file_type", self.language))
                yield Select(
                    [(v, v) for v in choices],
                    value=self.file_extension,
                    allow_blank=False,
                    id="file-type",
                )
                if self.saving:
                    yield Checkbox(tr("overwrite", self.language), id="overwrite")
                    yield Checkbox(tr("formulas", self.language), id="formulas")
                else:
                    yield Label(tr("encoding", self.language))
                    yield Select(
                        [(v, v) for v in ("auto", "utf-8-sig", "utf-16", "cp949")],
                        value="auto",
                        allow_blank=False,
                        id="encoding",
                    )
                if self.notice:
                    yield Static(Text(safe_text(self.notice, multiline=True)))
            yield Static("", id="form-error", classes="error")
            with Horizontal():
                yield Button(tr("cancel", self.language), id="cancel")
                yield Button(
                    tr("save" if self.saving else "open", self.language),
                    id="apply",
                    variant="primary",
                )

    def on_mount(self, event):
        event.prevent_default()
        self.query_one("#field-path", SafeInput).focus()

    def go_folder(self, folder):
        try:
            directory = Path(folder).expanduser().resolve()
            if not directory.is_dir():
                raise ValueError(tr("folder_missing", self.language))
            self.folder = directory
            drive = self.query_one("#drive", Select)
            roots = drive_roots(directory)
            canonical = next(
                (r for r in roots if r.casefold() == directory.anchor.casefold()), roots[0]
            )
            if drive.value != canonical:
                drive.set_options([(r, r) for r in roots])
                drive.value = canonical
            self.query_one("#folder-path", SafeInput).value = str(directory)
            tree = self.query_one("#file-tree", DirectoryTree)
            tree.path = directory
            if self.saving:
                field = self.query_one("#field-path", SafeInput)
                field.value = str(
                    directory / (Path(field.value).name or "Workbook" + self.file_extension)
                )
            self.query_one("#form-error", Static).update("")
        except (OSError, ValueError) as exc:
            self.query_one("#form-error", Static).update(Text(safe_text(exc)))

    @on(Button.Pressed)
    def pressed(self, event):
        event.prevent_default()
        key = event.button.id
        if key == "folder-up":
            self.go_folder(self.folder.parent)
        elif key == "folder-home":
            self.go_folder(Path.home())
        elif key == "folder-root":
            self.go_folder(self.folder.anchor)
        elif key == "folder-go":
            self.go_folder(self.query_one("#folder-path", SafeInput).value)
        elif key == "apply":
            self.confirm()
        elif key == "cancel":
            self.dismiss(None)
        event.stop()

    @on(SafeInput.Submitted)
    def input_submitted(self, event):
        event.prevent_default()
        if event.input.id == "folder-path":
            self.go_folder(event.value)
        else:
            self.confirm()
        event.stop()

    @on(DirectoryTree.DirectorySelected)
    def directory_selected(self, event):
        self.go_folder(event.path)
        event.stop()

    @on(DirectoryTree.FileSelected)
    def file_selected(self, event):
        event.prevent_default()
        self.query_one("#field-path", SafeInput).value = str(event.path)
        event.stop()

    @on(Select.Changed)
    def select_changed(self, event):
        if event.value is Select.NULL:
            return
        if event.select.id == "drive":
            if Path(event.value).anchor != self.folder.anchor:
                self.go_folder(event.value)
        elif event.select.id == "file-type" and event.value != self.file_extension:
            self.file_extension = event.value
            if self.saving:
                field = self.query_one("#field-path", SafeInput)
                if field.value:
                    field.value = str(Path(field.value).with_suffix(event.value))
            else:
                self.query_one(DirectoryTree).reload()

    def confirm(self):
        try:
            entered = self.query_one("#field-path", SafeInput).value.strip()
            if not entered:
                raise ValueError(tr("choose_file", self.language))
            path = Path(entered).expanduser()
            path = (self.folder / path if not path.is_absolute() else path).resolve()
            if path.is_dir():
                self.go_folder(path)
                return
            if self.saving and not path.suffix:
                path = path.with_suffix(self.file_extension)
            if self.saving and path.suffix.lower() not in self.allowed_extensions:
                raise ValueError("Supported save formats: " + ", ".join(self.allowed_extensions))
            values = {
                "path": str(path),
                "overwrite": self.query_one("#overwrite", Checkbox).value if self.saving else False,
                "formulas": self.query_one("#formulas", Checkbox).value if self.saving else False,
                "encoding": "auto" if self.saving else self.query_one("#encoding", Select).value,
            }
            result = self.submit(values)
        except (ValueError, OSError, TypeError, ArithmeticError) as exc:
            self.query_one("#form-error", Static).update(Text(safe_text(exc, multiline=True)))
            return
        self.dismiss(result if result is not None else values)
