from rich.rule import Rule
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Select, Static, Switch, TextArea

from agent_console.launcher.command import LaunchRequest, preflight
from agent_console.launcher.controller import LaunchController, workspace_result
from agent_console.launcher.profile import LaunchError, ProfileBook, RuntimeProfile
from agent_console.ui.controls import ActionButton, ConsoleHeader
from agent_console.ui.monitor import MonitorScreen


class ConfirmRun(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmRun { align: center middle; background: $background 70%; }
    #confirm-dialog { width: 78; max-width: 95%; height: auto; max-height: 95%;
                      padding: 1 2; border: round $foreground 25%; background: $surface; }
    #confirm-title { text-style: bold; margin-bottom: 1; }
    #confirm-values { height: auto; }
    #confirm-warning { height: auto; color: $text-muted; margin: 1 0; }
    #confirm-buttons { height: 3; }
    #confirm-buttons Button { margin-right: 2; }
    """
    BINDINGS = [("escape", "dismiss(False)", "Cancel")]

    def __init__(self, profile: RuntimeProfile, request: LaunchRequest) -> None:
        super().__init__()
        # Do not retain or repeat the prompt in the confirmation screen.
        values = [
            ("Runtime", profile.name),
            ("Workspace", request.workspace),
            ("Task", request.task.capitalize()),
            ("Provider", request.provider.capitalize()),
            ("Model", request.model),
            ("Verify", request.verify),
            ("Retries", str(request.max_retries)),
            ("Execution", "ENABLED" if request.allow_execution else "OFF"),
        ]
        self.configuration = Text()
        for key, value in values:
            self.configuration.append(f"{key:<12}", style="dim")
            self.configuration.append(
                value + "\n",
                style=("bold yellow" if key == "Execution" and request.allow_execution else "bold"),
            )
        self.description = self.configuration.plain

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="confirm-dialog"):
            yield Static("Start agent run?", id="confirm-title")
            yield Static(self.configuration, id="confirm-values")
            yield Static(
                "Execution may modify workspace files and run tools.\n"
                "ai-agent remains the final authority.",
                id="confirm-warning",
            )
            with Horizontal(id="confirm-buttons"):
                yield ActionButton("Cancel", id="dismiss-confirm")
                yield ActionButton("Start", id="confirm-start", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#dismiss-confirm", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-start")


class LauncherScreen(Screen):
    BINDINGS = [("tab", "app.focus_next", "Next"), ("shift+tab", "app.focus_previous", "Previous")]
    DEFAULT_CSS = """
    LauncherScreen { background: $surface; }
    #launch-form { padding: 0 2; }
    #launch-form Label { height: 1; }
    #launch-form .title { height: 1; text-style: bold; }
    #launch-form .help { height: 1; color: $text-muted; }
    #launch-form Input, #launch-form Select { width: 100%; height: 3; }
    #launch-form Input, #prompt { border: round $foreground 35%; }
    #launch-form Select > SelectCurrent { border: round $foreground 35%; }
    #launch-form Select > SelectOverlay {
        border: solid $foreground 60% !important; background: $panel; padding: 0;
    }
    #launch-form Select:focus > SelectCurrent { border: solid $primary; }
    #runtime-row { height: 3; }
    #runtime-row Label { width: 16; height: 3; content-align: left middle; }
    #runtime-row Select { width: 1fr; }
    #workspace-heading { height: 1; }
    #workspace-heading Label { width: auto; }
    #workspace-state { width: auto; margin-left: 2; text-style: bold; }
    #workspace-state.valid { color: $success; }
    #workspace-state.invalid { color: $error; }
    #workspace-state.checking { color: $primary; }
    #run-settings { grid-size: 2; grid-rows: 4 5 4; grid-gutter: 0 2; height: 13; }
    #run-settings > Vertical { height: auto; }
    LauncherScreen.narrow #run-settings { grid-size: 1; grid-rows: 4 4 5 5 4 4; height: 26; }
    LauncherScreen.short #runtime-row, LauncherScreen.short #runtime-row Label,
    LauncherScreen.short #runtime-row Select { height: 1; }
    LauncherScreen.short #launch-form .help { display: none; }
    LauncherScreen.short #run-settings { grid-rows: 2 2 2; height: 6; }
    LauncherScreen.short.narrow #run-settings { grid-rows: 2 2 2 2 2 2; height: 12; }
    LauncherScreen.short #run-settings > Vertical {
        layout: horizontal; height: 2; border-bottom: solid $foreground 20%;
    }
    LauncherScreen.short #run-settings Label { width: 12; height: 1; }
    LauncherScreen.short #run-settings Input,
    LauncherScreen.short #run-settings Select { width: 1fr; height: 1; }
    LauncherScreen.short #run-settings Input,
    LauncherScreen.short Select > SelectCurrent {
        border-left: solid $foreground 40% !important;
        border-right: solid $foreground 40% !important;
        background: $panel; padding: 0 1;
    }
    LauncherScreen.short #run-settings Input:focus,
    LauncherScreen.short Select:focus > SelectCurrent {
        background: $primary-muted; text-style: bold underline;
    }
    #allow-execution { height: 1; padding: 0; border: none; margin-top: 1; }
    #allow-execution:focus { background-tint: $foreground 15%; }
    #allow-execution .switch--slider { color: $foreground 60%; }
    #allow-execution.-on .switch--slider { color: $warning; }
    LauncherScreen.short #allow-execution { margin-top: 0; }
    LauncherScreen.short #run-settings #execution-state { width: 27; }
    #execution-state.enabled { color: $warning; text-style: bold; }
    #execution-note { height: auto; color: $text-muted; }
    #prompt-heading { height: 1; }
    #prompt-heading Label { width: 1fr; }
    #prompt-heading Button { margin-left: 1; }
    #prompt { height: 5; }
    #prompt:focus { border: solid $primary; }
    #launch-status { height: auto; max-height: 3; overflow-y: auto; margin: 0 2; }
    #launch-buttons { height: 3; margin: 0 2; }
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
        self.prompt_height: int | None = None

    def compose(self) -> ComposeResult:
        yield ConsoleHeader()
        with VerticalScroll(id="launch-form", can_focus=False):
            yield Static(Rule("New agent run", align="left", style="dim"), classes="title")
            with Horizontal(id="runtime-row"):
                yield Label("Runtime profile")
                yield Select(
                    [(name, name) for name in self.book.profiles],
                    id="profile",
                    value=self.selected if self.selected else Select.NULL,
                    prompt="No runtime configured",
                    allow_blank=not self.book.profiles,
                )
            if not self.book.profiles:
                yield Static(
                    "No runtime configured. Register one using agent-console profile add, "
                    "then reopen launch. No process will be started.",
                    markup=False,
                )
            with Horizontal(id="workspace-heading"):
                yield Label("Workspace")
                yield Static("Unchecked", id="workspace-state", markup=False)
            yield Input(
                placeholder="Existing absolute directory",
                id="workspace",
                tooltip="Check before starting work; success is not execution approval.",
            )
            yield Static(
                "Check before starting work; success is not execution approval.", classes="help"
            )
            yield Static(Rule("Run settings", align="left", style="dim"), classes="title")
            with Grid(id="run-settings"):
                with Vertical():
                    yield Label("Task")
                    yield Select(
                        [("Developer", "developer")],
                        value="developer",
                        allow_blank=False,
                        id="task",
                    )
                with Vertical():
                    yield Label("Provider")
                    yield Select(
                        [("Codex", "codex")], value="codex", allow_blank=False, id="provider"
                    )
                with Vertical():
                    yield Label("Model")
                    yield Input(
                        id="model",
                        placeholder="Model from runtime profile",
                        tooltip="Override for this run only",
                    )
                    yield Static("Override for this run only", classes="help")
                with Vertical():
                    yield Label("Verify")
                    yield Select(
                        [(mode, mode) for mode in ("none", "pytest", "web")],
                        value="none",
                        allow_blank=False,
                        id="verify",
                    )
                    yield Static("No host verification", classes="help", id="verify-help")
                with Vertical():
                    yield Label("Retries 0–3")
                    yield Input("0", id="retries", type="integer", tooltip="Max retries: 0–3")
                with Vertical():
                    yield Label("Allow execution: OFF", id="execution-state")
                    yield Switch(
                        False,
                        animate=False,
                        id="allow-execution",
                        tooltip="Allow execution: click or press Space to toggle",
                    )
            yield Static(
                "Execution is OFF. ai-agent decides workspace and tool permissions.",
                id="execution-note",
            )
            with Horizontal(id="prompt-heading"):
                yield Label("Prompt")
                yield ActionButton(
                    "[-]",
                    id="prompt-smaller",
                    classes="prompt-size",
                    tooltip="Reduce prompt height",
                )
                yield ActionButton(
                    "[+]",
                    id="prompt-larger",
                    classes="prompt-size",
                    tooltip="Increase prompt height",
                )
                yield ActionButton(
                    "Auto",
                    id="prompt-auto",
                    classes="prompt-size",
                    tooltip="Restore automatic prompt height",
                )
            yield TextArea(
                id="prompt", tooltip="Not saved; cleared on Start, including undo history"
            )
            yield Static("Not saved · cleared on Start, including undo history", classes="help")
        yield Static(
            "Ready. Check Workspace before starting work.", id="launch-status", markup=False
        )
        with Horizontal(id="launch-buttons"):
            yield ActionButton(
                "Check Workspace", id="check-workspace", disabled=not self.book.profiles
            )
            yield ActionButton(
                "Start Run", id="start-run", variant="primary", disabled=not self.book.profiles
            )
            yield ActionButton("Quit", id="quit-launcher", classes="tertiary")
        yield Footer()

    def on_mount(self) -> None:
        self.layout_for_size()
        self.use_profile()

    def on_resize(self, event: Resize) -> None:
        self.layout_for_size()

    def layout_for_size(self) -> None:
        self.set_class(self.size.width < 110, "narrow")
        short = self.size.height < 36
        self.set_class(short, "short")
        self.set_class(self.size.width >= 110 and self.size.height >= 46, "roomy")
        if self.is_mounted:
            for selector in ("#profile", "#task", "#provider", "#model", "#verify", "#retries"):
                self.query_one(selector).compact = short
            self.size_prompt()

    def size_prompt(self) -> None:
        maximum = max(5, min(20, self.size.height - 10))
        automatic = 8 if self.has_class("roomy") else 5
        height = min(maximum, self.prompt_height or automatic)
        self.query_one("#prompt").styles.height = height
        self.query_one("#prompt-smaller", Button).disabled = height <= 5
        self.query_one("#prompt-larger", Button).disabled = height >= maximum

    def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "allow-execution":
            label = self.query_one("#execution-state", Label)
            label.update("Allow execution: ENABLED" if event.value else "Allow execution: OFF")
            label.set_class(event.value, "enabled")
            self.query_one("#execution-note", Static).update(
                "May change files and run tools. ai-agent remains the final authority."
                if event.value
                else "Execution is OFF. ai-agent decides workspace and tool permissions."
            )

    def show_workspace_state(self, state: str) -> None:
        widget = self.query_one("#workspace-state", Static)
        widget.update(state)
        widget.set_classes(state.lower())

    def use_profile(self) -> None:
        name = self.query_one("#profile", Select).value
        if isinstance(name, str) and name in self.book.profiles:
            profile = self.book.profiles[name]
            self.query_one("#model", Input).value = profile.model
            self.query_one("#verify", Select).value = profile.default_verify
            self.query_one("#retries", Input).value = str(profile.default_max_retries)
        self.query_one("#allow-execution", Switch).value = False

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "profile":
            self.use_profile()
            self.invalidate_check()
        elif event.select.id == "verify":
            help_text = {
                "none": "No host verification",
                "pytest": "Run pytest validation",
                "web": "Run pytest + local web verification",
            }
            self.query_one("#verify-help", Static).update(help_text.get(str(event.value), ""))
            event.select.tooltip = help_text.get(str(event.value), "")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "workspace":
            self.invalidate_check()

    def invalidate_check(self) -> None:
        self.show_workspace_state("Unchecked")
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
            allow_execution=False if check else self.query_one("#allow-execution", Switch).value,
        )
        preflight(profile, request, check=check)
        return profile, request

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("prompt-smaller", "prompt-larger", "prompt-auto"):
            height = int(self.query_one("#prompt").styles.height.value)
            self.prompt_height = (
                None
                if event.button.id == "prompt-auto"
                else max(
                    5,
                    min(
                        max(5, min(20, self.size.height - 10)),
                        height + (3 if event.button.id == "prompt-larger" else -3),
                    ),
                )
            )
            self.size_prompt()
            return
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
            if event.button.id == "check-workspace":
                self.show_workspace_state("Invalid")
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
            self.query_one("#allow-execution", Switch).value = False
        except LaunchError as error:
            self.show_status(str(error))

    def open_monitor(self, profile: RuntimeProfile, request: LaunchRequest, *, check: bool) -> None:
        source = self.controller.begin(profile, request, check=check)
        if check:
            self.show_workspace_state("Checking")
        key = (profile.name, request.workspace)

        def back() -> None:
            session = self.controller.session
            self.app.pop_screen()
            if check:
                self.check_key = key
                result = workspace_result(session)
                self.show_workspace_state("Valid" if result.startswith("Valid") else "Invalid")
                self.show_status(result)
            else:
                self.show_status(
                    f"Run ended · Console exit {session.exit_code}. "
                    "Prompt cleared; prepare a new request."
                )

        self.app.push_screen(MonitorScreen(source, self.controller.session, on_back=back))


class LauncherApp(App[int]):
    TITLE = "AGENT CONSOLE"
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
