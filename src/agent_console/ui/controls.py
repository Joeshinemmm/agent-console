"""Shared action styling: keyboard focus is a border, never reversed label text."""

from textual.widgets import Button


class ActionButton(Button):
    DEFAULT_CSS = """
    ActionButton.-style-default {
        height: 3; min-width: 12; border: round $border-blurred;
        background: $surface-lighten-1; color: $text; text-style: bold;
        &.-primary { background: $primary; color: $text; border: round $primary; }
        &.-warning { background: $warning-muted; color: $text-warning;
                     border: round $warning; }
        &.tertiary { background: $surface; border: round $surface; }
        &:hover { background: $boost; border: round $foreground; }
        &:focus { text-style: bold; background-tint: transparent; border: solid $primary; }
        &.-active { text-style: bold underline; background: $primary-muted;
                    border: solid $primary; tint: transparent; }
        &:disabled { text-style: dim; text-opacity: 0.45; background: $surface;
                      color: $text-muted; border: round $surface; }
    }
    """
