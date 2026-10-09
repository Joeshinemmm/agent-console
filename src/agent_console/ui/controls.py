"""Shared action styling: keyboard focus is a border, never reversed label text."""

from textual.widgets import Button, Static


class ActionButton(Button, inherit_css=False):
    DEFAULT_CSS = """
    ActionButton {
        width: auto; height: 3; min-width: 12; padding: 0 1; line-pad: 1;
        pointer: pointer;
        border: round $foreground 40%; content-align: center middle;
        background: $surface-lighten-1; color: $text; text-style: bold;
        &.-primary { background: $primary-muted; color: $text; border: round $primary; }
        &.-warning { background: $warning-muted; color: $text-warning;
                     border: round $warning; }
        &.tertiary { background: $surface; }
        &:hover { background-tint: $foreground 10%; }
        &:focus { text-style: bold; border: solid $foreground; }
        &.-active { text-style: bold underline; tint: $foreground 15%; }
        &:disabled { text-style: none; text-opacity: 1; background: $surface;
                      color: $foreground 60%; border: round $foreground 20%;
                      background-tint: transparent; tint: transparent; pointer: not-allowed; }
        &.prompt-size { height: 1; min-width: 5; padding: 0; border: none;
                       text-style: none; background: $panel; }
        &.prompt-size:focus { text-style: bold underline; }
    }
    """


class ConsoleHeader(Static):
    """A title without Textual's unused command-palette icon or click actions."""

    DEFAULT_CSS = """
    ConsoleHeader { dock: top; height: 1; width: 100%; background: $panel;
                    color: $foreground; content-align: center middle; }
    """

    def __init__(self) -> None:
        super().__init__("AGENT CONSOLE")
