from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from agent_console.models.run import RunState, Status
from agent_console.presentation import STYLES

AGENTS = ("developer", "codex", "test", "browser", "desktop", "training")


def system_text(run: RunState) -> Text:
    """Keep pipeline and unknown components accessible without crowding the agents."""
    text = Text("System: ", style="dim")
    for name, status in run.components:
        if name not in AGENTS:
            if text.plain != "System: ":
                text.append(" · ")
            text.append(f"{name.capitalize()} {status}", style=STYLES[status])
    return text if text.plain != "System: " else Text()


class Components(Static):
    def show_run(self, run: RunState) -> None:
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(width=16)
        table.add_column(ratio=1)
        states = dict(run.components)
        for name in AGENTS:
            status = states.get(name, Status.IDLE)
            table.add_row(
                Text(name.capitalize(), style="dim" if status == Status.IDLE else "bold"),
                Text(str(status), style=STYLES[status]),
            )
        self.update(table)
