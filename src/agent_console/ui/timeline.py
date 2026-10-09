from rich.text import Text
from textual.widgets import DataTable

from agent_console.models.run import RunState
from agent_console.presentation import description, event_style

TIMELINE_LIMIT = 1000


class Timeline(DataTable):
    def on_mount(self) -> None:
        self.border_title = "Timeline"
        self.tooltip = "Sequence order · latest 1,000 events"
        self.add_columns("Seq", "Elapsed", "Component", "Event / activity")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def show_run(self, run: RunState) -> None:
        if getattr(self, "_shown_events", None) is run.events:
            return
        same_run = getattr(self, "_shown_run", None) == run.run_id
        follow = self.is_vertical_scroll_end
        scroll_y = self.scroll_y if same_run else 0
        cursor_row = self.cursor_row if same_run else 0
        self._shown_events = run.events
        self._shown_run = run.run_id
        self.clear()
        for event in run.events[-TIMELINE_LIMIT:]:
            style = event_style(event)
            self.add_row(
                str(event.sequence),
                f"{event.elapsed_ms / 1000:.3f}s",
                Text(event.component.capitalize(), style=style),
                Text(("ERROR · " if style else "") + description(event), style=style),
            )
        if follow or not same_run:
            self.move_cursor(row=max(0, self.row_count - 1), scroll=False)
            self.scroll_end(animate=False)
        else:
            self.move_cursor(row=min(cursor_row, self.row_count - 1), scroll=False)
            self.scroll_to(y=scroll_y, animate=False, force=True)
