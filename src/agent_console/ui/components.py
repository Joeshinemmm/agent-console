from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from agent_console.models.run import RunState
from agent_console.presentation import STYLES


class Components(Static):
    def show_run(self, run: RunState) -> None:
        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(ratio=1)
        table.add_column()
        for name, status in run.components:
            table.add_row(Text(name.capitalize()), Text(str(status), style=STYLES[status]))
        self.update(table)
