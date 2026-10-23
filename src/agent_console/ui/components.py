from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from agent_console.models.run import RunState, Status
from agent_console.presentation import STYLES, component_label, provider_label

AGENTS = ("developer", "llm", "test", "browser", "desktop", "training")


def agent_label(name: str, run: RunState) -> str:
    label = component_label(name)
    if name == "llm" and run.provider:
        label += f" ({provider_label(run.provider)})"
    return label


def system_text(run: RunState) -> Text:
    """Keep pipeline and unknown components accessible without crowding the agents."""
    text = Text("System: ", style="dim")
    for name, status in run.components:
        if name not in AGENTS:
            if text.plain != "System: ":
                text.append(" · ")
            text.append(f"{component_label(name)} {status}", style=STYLES[status])
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
                Text(agent_label(name, run), style="dim" if status == Status.IDLE else "bold"),
                Text(str(status), style=STYLES[status]),
            )
        self.update(table)
