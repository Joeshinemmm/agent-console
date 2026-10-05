from textual.app import App

from agent_console.sources import ClosableSource
from agent_console.state.session import Session
from agent_console.ui.monitor import MonitorScreen


class AgentConsole(App[int]):
    """Backward-compatible replay/run app using the shared monitor screen."""

    TITLE = "AGENT CONSOLE"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [("ctrl+c", "quit", "Stop")]

    def __init__(self, source: ClosableSource, session: Session) -> None:
        self.session = session
        self.monitor = MonitorScreen(source, session)
        super().__init__()

    def get_default_screen(self) -> MonitorScreen:
        return self.monitor

    def refresh_session(self, force: bool = False) -> None:
        self.monitor.refresh_session(force)

    async def action_quit(self) -> None:
        await self.monitor.action_quit()
