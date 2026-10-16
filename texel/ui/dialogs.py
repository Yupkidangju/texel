from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DirectoryTree,
    Input,
    Label,
    OptionList,
    Select,
    Static,
)
from textual.widgets.option_list import Option

from ..i18n import tr
from .safe_text import SafeInput, safe_text


@dataclass
class Field:
    key: str
    value: object = ""
    options: list[str] | None = None


class FormDialog(ModalScreen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        Binding("tab", "app.focus_next", show=False, priority=True),
        Binding("shift+tab", "app.focus_previous", show=False, priority=True),
    ]
    DEFAULT_CSS = """
    FormDialog { align: center middle; background: $background 65%; }
    FormDialog > Vertical { width: 72; max-width: 95%; max-height: 92%; height: 34; border: round $accent; background: $surface; padding: 1 2; }
    FormDialog .form-title { text-style: bold; color: $accent; margin-bottom: 1; }
    FormDialog VerticalScroll { height: 1fr; min-height: 1; }
    FormDialog .form-notice { height: auto; max-height: 3; overflow-y: auto; }
    FormDialog Input, FormDialog Select { margin-bottom: 1; }
    FormDialog .error { color: $error; height: auto; max-height: 2; overflow-y: auto; }
    FormDialog Horizontal { height: 3; align-horizontal: right; }
    FormDialog Button { margin-left: 1; }
    FormDialog DirectoryTree { height: 8; border: solid $panel; }
    """

    def __init__(self, title, fields, submit, language="ko", notice="", browse=None):
        super().__init__()
        self.title_text, self.fields, self.submit = title, fields, submit
        self.language, self.notice, self.browse = language, notice, browse

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(tr(self.title_text, self.language), classes="form-title")
            if self.notice:
                yield Static(Text(safe_text(self.notice, multiline=True)), classes="form-notice")
            with VerticalScroll():
                for field in self.fields:
                    if isinstance(field.value, bool):
                        yield Checkbox(
                            tr(field.key, self.language), value=field.value, id="field-" + field.key
                        )
                    else:
                        yield Label(tr(field.key, self.language))
                        if field.options:
                            yield Select(
                                [(tr(v, self.language), v) for v in field.options],
                                value=field.value,
                                allow_blank=False,
                                id="field-" + field.key,
                            )
                        else:
                            yield SafeInput(str(field.value), id="field-" + field.key)
                if self.browse:
                    yield DirectoryTree(self.browse, id="file-tree")
            yield Static("", id="form-error", classes="error")
            with Horizontal():
                yield Button(tr("cancel", self.language), id="cancel")
                yield Button(tr("apply", self.language), id="apply", variant="primary")

    def on_mount(self):
        fields = list(self.query("Input, Select, Checkbox"))
        if fields:
            fields[0].focus()

    @on(DirectoryTree.FileSelected)
    def file_selected(self, event):
        self.query_one("#field-path", Input).value = str(event.path)

    @on(Input.Submitted)
    def input_submitted(self):
        self.confirm()

    @on(Button.Pressed)
    def pressed(self, event):
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "apply":
            self.confirm()

    def confirm(self):
        values = {}
        for field in self.fields:
            widget = self.query_one("#field-" + field.key)
            values[field.key] = widget.value
        try:
            result = self.submit(values)
        except (ValueError, OSError, TypeError, ArithmeticError) as exc:
            self.query_one("#form-error", Static).update(Text(safe_text(exc, multiline=True)))
            return
        self.dismiss(result if result is not None else values)

    def action_cancel(self):
        self.dismiss(None)


class CommandDialog(ModalScreen):
    BINDINGS = [("escape", "cancel", "Cancel")]
    DEFAULT_CSS = """
    CommandDialog { align: center middle; background: $background 65%; }
    CommandDialog > Vertical { width: 68; max-width: 95%; height: auto; max-height: 85%; border: round $accent; background: $surface; padding: 1 2; }
    CommandDialog OptionList { height: auto; min-height: 3; max-height: 20; border: none; }
    CommandDialog Input { margin-bottom: 1; }
    """

    def __init__(self, commands, language="ko", title="search_commands"):
        super().__init__()
        self.commands, self.language, self.title_key = commands, language, title
        self._search_key_queue = []
        self._search_flush_scheduled = False

    def compose(self):
        with Vertical():
            yield Label(tr(self.title_key, self.language))
            yield SafeInput(placeholder=tr("search_commands", self.language), id="command-search")
            yield OptionList(id="command-list")

    def on_mount(self):
        self.rebuild("")
        self.query_one(Input).focus()

    def rebuild(self, query):
        query = query.casefold()
        options = self.query_one(OptionList)
        options.clear_options()
        for command in self.commands:
            title = tr(command.key, self.language)
            if query in (command.key + " " + title).casefold():
                options.add_option(
                    Option(Text(f"{title:<24} {command.shortcut}  · {command.key}"), id=command.key)
                )
        if options.option_count:
            options.highlighted = 0

    @on(Input.Changed)
    def search(self, event):
        self.rebuild(event.value)

    @on(Input.Submitted)
    def submit_search(self):
        options = self.query_one(OptionList)
        if options.highlighted is not None:
            self.dismiss(options.get_option_at_index(options.highlighted).id)

    @on(OptionList.OptionSelected)
    def selected(self, event):
        self.dismiss(event.option.id)

    def on_key(self, event):
        if event.is_printable or event.key == "enter":
            # 첫 layout 전에 화면으로 전달된 키도 검색 입력의 순서를 유지한다.
            self._search_key_queue.append((event.key, event.character))
            if not self._search_flush_scheduled:
                self._search_flush_scheduled = True
                self.call_after_refresh(self.flush_search_keys)
            event.stop()
            event.prevent_default()
            return
        if event.key in {"down", "up"} and self.query_one(Input).has_focus:
            self.query_one(OptionList).focus()
            event.stop()
            event.prevent_default()

    def flush_search_keys(self):
        queued, self._search_key_queue = self._search_key_queue, []
        self._search_flush_scheduled = False
        if not self.is_active:
            return
        search = self.query_one(Input)
        for key, character in queued:
            if key == "enter":
                self.rebuild(search.value)
                self.submit_search()
                break
            if character is not None:
                search.insert_text_at_cursor(character)

    def action_cancel(self):
        self.dismiss(None)


class TextDialog(ModalScreen):
    BINDINGS = [("escape", "close", "Close")]
    DEFAULT_CSS = """
    TextDialog { align: center middle; background: $background 65%; }
    TextDialog > Vertical { width: 100; max-width: 95%; height: 85%; border: round $accent; background: $surface; padding: 1 2; }
    TextDialog .text-title { height: 2; color: $accent; text-style: bold; }
    TextDialog VerticalScroll { height: 1fr; }
    TextDialog Button { align-horizontal: right; margin-top: 1; }
    """

    def __init__(self, title, content, language="ko"):
        super().__init__()
        self.title_text, self.content, self.language = title, content, language

    def compose(self):
        with Vertical():
            yield Label(tr(self.title_text, self.language), classes="text-title")
            with VerticalScroll():
                yield Static(Text(safe_text(self.content, multiline=True)))
            yield Button(tr("close", self.language), id="close", variant="primary")

    @on(Button.Pressed)
    def close_button(self):
        self.dismiss()

    def action_close(self):
        self.dismiss()
