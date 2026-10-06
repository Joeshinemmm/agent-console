"""Shared action styling: keyboard focus is a border, never reversed label text."""

from textual.widgets import Button


class ActionButton(Button):
    DEFAULT_CSS = """
    ActionButton.-style-default {
        height: 3; min-width: 12; padding: 0 1; line-pad: 1;
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
                      background-tint: transparent; tint: transparent; }
    }
    """
