from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Select, Static, TextArea

from agent_console.launcher.command import LaunchRequest, preflight
from agent_console.launcher.controller import LaunchController, workspace_result
from agent_console.launcher.profile import LaunchError, ProfileBook, RuntimeProfile
from agent_console.ui.monitor import MonitorScreen


class ConfirmRun(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmRun { align: center middle; background: $background 70%; }
    #confirm-dialog { width: 76; max-width: 95%; height: auto; max-height: 95%;
                      padding: 1 2; border: round $warning; background: $surface; }
    #confirm-dialog Static { height: auto; margin-bottom: 1; }
    #confirm-buttons { height: 3; }
    #confirm-buttons Button { margin-right: 2; }
    """
    BINDINGS = [("escape", "dismiss(False)", "Cancel")]

    def __init__(self, profile: RuntimeProfile, request: LaunchRequest) -> None:
        super().__init__()
        # Do not retain or repeat the prompt in the confirmation screen.
        self.description = (
            f"Start Agent Run?\n\nRuntime: {profile.name}\n"
            f"Workspace: {request.workspace}\nTask: {request.task}\nProvider: {request.provider}\n"
            f"Model: {request.model}\nVerify: {request.verify}\nRetries: {request.max_retries}\n"
            f"Execution: {'ENABLED' if request.allow_execution else 'OFF'}\n\n"
            "Execution may modify workspace files and run tools. ai-agent remains the final "
            "authority for workspace and execution policy."
        )

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="confirm-dialog"):
            yield Static(self.description, markup=False)
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel", id="dismiss-confirm")
                yield Button("Start", id="confirm-start", variant="warning")

    def on_mount(self) -> None:
        self.query_one("#dismiss-confirm", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-start")


class LauncherScreen(Screen):
    DEFAULT_CSS = """
    LauncherScreen { background: $surface; }
    #launch-form { padding: 1 2; }
    #launch-form Label { margin-top: 1; }
    #launch-form Input, #launch-form Select { width: 100%; }
    #prompt { height: 8; min-height: 5; border: round $primary; }
    #execution-note { color: $warning; height: auto; }
    #launch-status { height: auto; max-height: 6; margin: 0 2; }
    #launch-buttons { height: 3; margin: 1 2; }
    #launch-buttons Button { margin-right: 1; }
    """

    def __init__(
        self, book: ProfileBook, controller: LaunchController, selected: str | None = None
    ) -> None:
        super().__init__()
        self.book = book
        self.controller = controller
        self.selected = selected or book.default_profile
        self.pending: tuple[RuntimeProfile, LaunchRequest] | None = None
        self.check_key: tuple[str, str] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="launch-form"):
            yield Static("New Run", classes="title")
            yield Label("Runtime profile")
            yield Select(
                [(name, name) for name in self.book.profiles],
                id="profile",
                value=self.selected if self.selected else Select.NULL,
                prompt="No runtime configured",
            )
            if not self.book.profiles:
                yield Static(
                    "No runtime configured. Register one using agent-console profile add, "
                    "then reopen launch. No process will be started.",
                    markup=False,
                )
            yield Label("Workspace · existing absolute directory")
            yield Input(placeholder="Target workspace", id="workspace")
            yield Label("Task")
            yield Select(
                [("Developer", "developer")], value="developer", allow_blank=False, id="task"
            )
            yield Label("Provider")
            yield Select([("Codex", "codex")], value="codex", allow_blank=False, id="provider")
            yield Label("Model · per-run override")
            yield Input(id="model", placeholder="Model from runtime profile")
            yield Label(
                "Verify · none: no host verification / pytest: tests / web: tests + local web"
            )
            yield Select(
                [(mode, mode) for mode in ("none", "pytest", "web")],
                value="none",
                allow_blank=False,
                id="verify",
            )
            yield Label("Max retries · 0–3")
            yield Input("0", id="retries", type="integer")
            yield Checkbox("Allow execution", value=False, id="allow-execution")
            yield Static(
                "OFF by default. Enabling permits file changes and tool execution under "
                "ai-agent policy. A workspace check is not approval.",
                id="execution-note",
            )
            yield Label("Prompt · kept only in memory for this run")
            yield TextArea(id="prompt")
        yield Static(
            "Ready. Check Workspace before starting work.", id="launch-status", markup=False
        )
        with Horizontal(id="launch-buttons"):
            yield Button("Check Workspace", id="check-workspace", disabled=not self.book.profiles)
            yield Button(
                "Start Run", id="start-run", variant="primary", disabled=not self.book.profiles
            )
            yield Button("Quit", id="quit-launcher")
        yield Footer()

    def on_mount(self) -> None:
        self.use_profile()

    def use_profile(self) -> None:
        name = self.query_one("#profile", Select).value
        if isinstance(name, str) and name in self.book.profiles:
            profile = self.book.profiles[name]
            self.query_one("#model", Input).value = profile.model
            self.query_one("#verify", Select).value = profile.default_verify
            self.query_one("#retries", Input).value = str(profile.default_max_retries)
        self.query_one("#allow-execution", Checkbox).value = False

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "profile":
            self.use_profile()
            self.invalidate_check()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "workspace":
            self.invalidate_check()

    def invalidate_check(self) -> None:
        if self.check_key is not None:
            self.check_key = None
            self.show_status("Workspace or profile changed. Run Check Workspace again.")

    def show_status(self, message: str) -> None:
        self.query_one("#launch-status", Static).update(message)

    def read_request(self, *, check: bool = False) -> tuple[RuntimeProfile, LaunchRequest]:
        name = self.query_one("#profile", Select).value
        if not isinstance(name, str):
            raise LaunchError("Select a runtime profile first.")
        profile = self.book.select(name)
        try:
            retry_count = int(self.query_one("#retries", Input).value) if not check else 0
        except ValueError:
            raise LaunchError("Max retries must be an integer from 0 to 3.") from None
        request = LaunchRequest(
            workspace=self.query_one("#workspace", Input).value.strip(),
            prompt="" if check else self.query_one("#prompt", TextArea).text,
            task=str(self.query_one("#task", Select).value),
            provider=str(self.query_one("#provider", Select).value),
            model=self.query_one("#model", Input).value.strip(),
            verify=str(self.query_one("#verify", Select).value),
            max_retries=retry_count,
            allow_execution=False if check else self.query_one("#allow-execution", Checkbox).value,
        )
        preflight(profile, request, check=check)
        return profile, request

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-launcher":
            self.app.exit(0)
            return
        if self.controller.active or self.pending is not None:
            self.show_status("A check, run, or confirmation is already active.")
            return
        try:
            if event.button.id == "check-workspace":
                profile, request = self.read_request(check=True)
                self.open_monitor(profile, request, check=True)
            elif event.button.id == "start-run":
                profile, request = self.read_request()
                self.pending = (profile, request)
                self.app.push_screen(ConfirmRun(profile, request), self.confirmed)
        except LaunchError as error:
            self.show_status(str(error))

    def confirmed(self, accepted: bool) -> None:
        pending, self.pending = self.pending, None
        if not accepted or pending is None:
            self.show_status("Start cancelled. No process was started.")
            return
        profile, request = pending
        try:
            self.open_monitor(profile, request, check=False)
            self.query_one("#prompt", TextArea).load_text("")
            self.query_one("#allow-execution", Checkbox).value = False
        except LaunchError as error:
            self.show_status(str(error))

    def open_monitor(self, profile: RuntimeProfile, request: LaunchRequest, *, check: bool) -> None:
        source = self.controller.begin(profile, request, check=check)
        key = (profile.name, request.workspace)

        def back() -> None:
            session = self.controller.session
            self.app.pop_screen()
            if check:
                self.check_key = key
                self.show_status(workspace_result(session))
            else:
                self.show_status(
                    f"Run ended · Console exit {session.exit_code}. "
                    "Prompt cleared; prepare a new request."
                )

        self.app.push_screen(MonitorScreen(source, self.controller.session, on_back=back))


class LauncherApp(App[int]):
    TITLE = "AGENT CONSOLE · NEW RUN"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(self, book: ProfileBook, selected: str | None = None) -> None:
        self.controller = LaunchController()
        self.launcher = LauncherScreen(book, self.controller, selected)
        super().__init__()

    def get_default_screen(self) -> LauncherScreen:
        return self.launcher

    async def action_quit(self) -> None:
        if isinstance(self.screen, MonitorScreen):
            await self.screen.action_quit()
        else:
            self.launcher.pending = None
            self.exit(0)
