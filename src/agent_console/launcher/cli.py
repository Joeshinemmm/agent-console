import json
from pathlib import Path

from agent_console.launcher.profile import RuntimeProfile, config_path, load_profiles, save_profiles


def add_commands(commands) -> None:
    launch = commands.add_parser("launch", help="Open the local Developer Run Launcher")
    launch.add_argument("--config", help="Override with an agent-console.local.toml file")
    launch.add_argument("--profile", help="Select a runtime for this launcher session")
    profile = commands.add_parser(
        "profile", help="Manage local runtime profiles (no runtime execution)"
    )
    profile.add_argument("--config", help="Override with an agent-console.local.toml file")
    actions = profile.add_subparsers(dest="profile_action", required=True)
    actions.add_parser("list", help="List profiles and the selected default")
    actions.add_parser("path", help="Show the local config location")
    for action in ("show", "select", "remove"):
        sub = actions.add_parser(action)
        sub.add_argument("name")
    add = actions.add_parser("add", help="Add a profile after checking files; no commands are run")
    add.add_argument("name")
    add.add_argument("--python", required=True, dest="python_executable")
    add.add_argument("--main", required=True, dest="ai_agent_main")
    add.add_argument("--model", required=True)
    add.add_argument("--provider", choices=["codex"], default="codex")
    add.add_argument("--verify", choices=["none", "pytest", "web"], default="none")
    add.add_argument("--max-retries", type=int, choices=range(4), default=0)


def profile_command(args) -> int:
    from agent_console.launcher.profile import LaunchError

    path = config_path(args.config)
    if args.profile_action == "path":
        print(path)
        return 0
    book = load_profiles(path)
    if args.profile_action == "list":
        for name in book.profiles:
            print(("* " if name == book.default_profile else "  ") + name)
        if not book.profiles:
            print("No runtime configured.")
        return 0
    if args.profile_action == "show":
        profile = book.select(args.name)
        # Local paths are intentionally shown to their owner, never written to logs.
        print(
            json.dumps(
                {
                    "name": profile.name,
                    "python_executable": profile.python_executable,
                    "ai_agent_main": profile.ai_agent_main,
                    "provider": profile.provider,
                    "model": profile.model,
                    "default_verify": profile.default_verify,
                    "default_max_retries": profile.default_max_retries,
                },
                indent=2,
            )
        )
        return 0
    if args.profile_action == "add":
        if args.name in book.profiles:
            raise LaunchError("Profile already exists; choose a new name or explicitly remove it.")
        profile = RuntimeProfile(
            args.name,
            str(Path(args.python_executable).absolute()),
            str(Path(args.ai_agent_main).absolute()),
            args.model,
            args.provider,
            args.verify,
            args.max_retries,
        )
        profile.validate_files()
        book.profiles[profile.name] = profile
        if book.default_profile is None:
            book.default_profile = profile.name
    elif args.profile_action == "select":
        book.select(args.name)
        book.default_profile = args.name
    elif args.profile_action == "remove":
        book.select(args.name)
        del book.profiles[args.name]
        if book.default_profile == args.name:
            book.default_profile = next(iter(book.profiles), None)
    save_profiles(path, book)
    print("Runtime profiles saved. No runtime was executed.")
    return 0
