from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from agent_console.models.run import RunState, Status
from agent_console.presentation import STYLES


class Components(Static):
    def show_run(self, run: RunState) -> None:
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(width=16)
        table.add_column(ratio=1)
        for name, status in sorted(run.components, key=lambda item: item[1] == Status.IDLE):
            table.add_row(
                Text(name.capitalize(), style="dim" if status == Status.IDLE else "bold"),
                Text(str(status), style=STYLES[status]),
            )
        self.update(table)
