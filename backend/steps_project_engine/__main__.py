import argparse
import sys

from .manage import (
    create_container,
    exec_command,
    get_latest_conversation,
    list_containers,
    remove_container,
    run_agent,
)


def main():
    """
    This is an unimportant main file. The functions will be used by more important modules.
    Not this module itself.

    DO not even try to catch errors here.
    """
    parser = argparse.ArgumentParser(
        description="Container Management Script for cursor-agent",
        prog="python manage.py",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new container")
    create_parser.add_argument("user_id", help="User identifier")
    create_parser.add_argument("project_id", help="Project identifier")

    # remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a container")
    remove_parser.add_argument("user_id", help="User identifier")
    remove_parser.add_argument("project_id", help="Project identifier")
    remove_parser.add_argument(
        "--force", action="store_true", help="Force removal if container is running"
    )
    remove_parser.add_argument(
        "--remove-dir",
        action="store_true",
        help="Keep project directory (default: keep directory)",
    )

    # list command
    list_parser = subparsers.add_parser("list", help="List containers")
    list_parser.add_argument(
        "user_id", nargs="?", help="Optional user ID to filter containers"
    )

    # exec command
    exec_parser = subparsers.add_parser("exec", help="Execute a command in a container")
    exec_parser.add_argument("user_id", help="User identifier")
    exec_parser.add_argument("project_id", help="Project identifier")
    exec_parser.add_argument(
        "cmd", nargs=argparse.REMAINDER, help="Command to execute", metavar="command"
    )

    # agent command
    agent_parser = subparsers.add_parser(
        "agent", help="Run cursor-agent with structured output"
    )
    agent_parser.add_argument("user_id", help="User identifier")
    agent_parser.add_argument("project_id", help="Project identifier")
    agent_parser.add_argument("prompt", help="Prompt for the agent")
    agent_parser.add_argument("--session-id", "-s", help="Session ID to resume")

    # deps command
    deps_parser = subparsers.add_parser(
        "deps", help="Get Python package dependencies from container"
    )
    deps_parser.add_argument("user_id", help="User identifier")
    deps_parser.add_argument("project_id", help="Project identifier")

    # debug command
    debug_parser = subparsers.add_parser(
        "debug", help="Start a debug session with debugpy"
    )
    debug_parser.add_argument("user_id", help="User identifier")
    debug_parser.add_argument("project_id", help="Project identifier")
    debug_parser.add_argument(
        "--code-file",
        default="main.py",
        help="Code file to debug (default: main.py)",
    )

    # conversation command
    conversation_parser = subparsers.add_parser(
        "conversation", help="Get latest conversation history for a project"
    )
    conversation_parser.add_argument("user_id", help="User identifier")
    conversation_parser.add_argument("project_id", help="Project identifier")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "create":
        result = create_container(args.user_id, args.project_id)
        print(result["message"])
        if "project_dir" in result:
            print(f"Project directory: {result['project_dir']}")
        if result["status"] == "error":
            print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "remove":
        result = remove_container(
            args.user_id, args.project_id, args.force, args.remove_dir
        )
        print(result["message"])
        if result["status"] == "error":
            print(f"Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "list":
        containers = list_containers(args.user_id)
        if containers:
            print(f"{'Container Name':<40} {'Status':<30} {'Image'}")
            print("-" * 100)
            for container in containers:
                print(
                    f"{container['name']:<40} {container['status']:<30} {container['image']}"
                )
        else:
            print("No containers found")

    elif args.command == "exec":
        if not args.cmd:
            print("Error: command is required", file=sys.stderr)
            sys.exit(1)
        result = exec_command(args.user_id, args.project_id, args.cmd)
        if result["status"] == "success":
            print(result["stdout"])
        else:
            print(f"Error: {result['stderr']}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "agent":
        result = run_agent(
            args.user_id, args.project_id, args.prompt, resume_latest=True
        )

        if result["status"] == "success":
            print(result["final_result"]["result"])
        else:
            print(
                f"Error: {result.get('stderr', result.get('error', 'Unknown error'))}",
                file=sys.stderr,
            )
            sys.exit(1)

    elif args.command == "conversation":
        import json

        conversation_turns = get_latest_conversation(args.user_id, args.project_id)
        if conversation_turns:
            print(json.dumps(conversation_turns, indent=2))
        else:
            print("No conversation history found")


if __name__ == "__main__":
    main()
