from rich.text import Text
from textual import on
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option

from ..i18n import tr


class ContextMenu(ModalScreen):
    BINDINGS = [("escape", "close", "Close")]
    DEFAULT_CSS = """
    ContextMenu { background: transparent; align: left top; }
    ContextMenu > Vertical { width: 42; max-width: 96%; height: auto; max-height: 100%; border: round $accent; background: $surface; padding: 0 1; }
    ContextMenu Label { height: 1; color: $accent; text-style: bold; }
    ContextMenu OptionList { height: 1fr; min-height: 1; border: none; }
    """

    def __init__(self, commands, x, y, language="ko"):
        super().__init__()
        self.commands, self.x, self.y, self.language = commands, x, y, language
        self._dismiss_requested = False

    def compose(self):
        with Vertical(id="context-box"):
            yield Label(tr("context_menu", self.language))
            yield OptionList(
                *[
                    Option(
                        Text(tr(c.key, self.language) + ("   " + c.shortcut if c.shortcut else "")),
                        id=c.key,
                    )
                    for c in self.commands
                ],
                id="context-options",
            )

    def on_mount(self):
        self.fit_menu()
        options = self.query_one(OptionList)
        options.highlighted = 0
        options.focus()

    def fit_menu(self):
        box = self.query_one("#context-box")
        height = min(len(self.commands) + 3, 23, max(6, self.app.size.height - 2))
        box.styles.height = height
        box.styles.offset = (
            max(0, min(self.x, self.app.size.width - 42)),
            max(0, min(self.y, self.app.size.height - height)),
        )

    def on_resize(self):
        if self.is_mounted:
            self.fit_menu()

    def close_menu(self, result=None):
        if not self._dismiss_requested and self.is_active:
            self._dismiss_requested = True
            self.dismiss(result)

    @on(OptionList.OptionSelected)
    def selected(self, event):
        event.stop()
        self.close_menu(event.option.id)

    def on_click(self, event):
        if not self.query_one("#context-box").region.contains(event.screen_x, event.screen_y):
            self.close_menu()
        event.stop()

    def action_close(self):
        self.close_menu()
