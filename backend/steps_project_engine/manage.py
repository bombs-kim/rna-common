import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from settings import settings

from .prompt import SYSTEM_PROMPT

# TODO: Define more detailed Exceptions
# TODO: Consider using Docker network for container-to-container communication to reduce port mapping overhead

################################################################################
# Helper functions
################################################################################


def _run_command(cmd, capture_output=True, text=True, check=False, **kwargs):
    """
    Run a subprocess command with improved error messages.

    Args:
        cmd: Command to run (list or string)
        capture_output: Whether to capture stdout/stderr
        text: Whether to return text instead of bytes
        check: Whether to raise exception on non-zero exit
        **kwargs: Additional arguments to pass to subprocess.run

    Returns:
        subprocess.CompletedProcess result

    Raises:
        RuntimeError: If check=True and command fails, with detailed error message
    """
    try:
        result = subprocess.run(
            cmd, capture_output=capture_output, text=text, check=check, **kwargs
        )
        return result
    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Command failed: {' '.join(cmd) if isinstance(cmd, list) else cmd}\n"
        )
        if e.stdout:
            error_msg += f"stdout: {e.stdout}\n"
        if e.stderr:
            error_msg += f"stderr: {e.stderr}\n"
        raise RuntimeError(error_msg) from e


def _get_project_dir(user_id: str, project_id: str) -> Path:
    """
    Get the project directory path (for metadata storage).

    Returns:
        Path: Project directory path (e.g., project_containers/m/n)
    """
    return settings.PROJECT_CONTAINERS_DIR / user_id / project_id


def _get_latest_session_id(user_id: str, project_id: str) -> str | None:
    """
    Get the latest session ID from stream events files in the project directory.

    Args:
        user_id: User identifier
        project_id: Project identifier

    Returns:
        str | None: The latest session ID if found, None otherwise
    """
    project_dir = _get_project_dir(user_id, project_id)
    if not project_dir.exists():
        return None

    # Find all stream events files matching the pattern: YYYYMMDD_HH:MM_<session_id>_stream_events.jsonl
    stream_files = list(project_dir.glob("*_*_*_stream_events.jsonl"))
    if not stream_files:
        return None

    # Sort by modification time (most recent first)
    stream_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

    # Extract session_id from the most recent file
    # Format: YYYYMMDD_HH:MM_<session_id>_stream_events.jsonl
    latest_file = stream_files[0]
    parts = latest_file.stem.split("_")
    if len(parts) >= 3:
        # Session ID is the third part (index 2)
        return parts[2]

    return None


def get_container_data_dir(user_id: str, project_id: str) -> Path:
    """
    Get the container data directory path.

    Returns:
        Path: Container data directory path (e.g., project_containers/m/n/data)
    """
    return _get_project_dir(user_id, project_id) / "data"


def _create_project_directory(user_id: str, project_id: str) -> Path:
    """
    Create a dedicated directory for the project and its data subdirectory.

    Returns:
        Path: Created project directory path
    """
    project_path = _get_project_dir(user_id, project_id)
    project_path.mkdir(parents=True, exist_ok=True)
    get_container_data_dir(user_id, project_id).mkdir(parents=True, exist_ok=True)
    return project_path


def _check_container_exists(container_name: str) -> bool:
    """
    Check if a container exists (running or stopped).

    Args:
        container_name: Name of the container to check

    Returns:
        bool: True if container exists, False otherwise
    """
    check_result = _run_command(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"name={container_name}",
            "--format",
            "{{.Names}}",
        ],
        capture_output=True,
        text=True,
    )
    return container_name in check_result.stdout


def _check_container_running(container_name: str) -> bool:
    """
    Check if a container is currently running.

    Args:
        container_name: Name of the container to check

    Returns:
        bool: True if container is running, False otherwise
    """
    running_check = _run_command(
        [
            "docker",
            "ps",
            "--filter",
            f"name={container_name}",
            "--format",
            "{{.Names}}",
        ],
        capture_output=True,
        text=True,
    )
    return container_name in running_check.stdout


################################################################################
# Main functions
################################################################################


def create_container(user_id: str, project_id: str) -> dict:
    """
    Create a cursor-agent container with dynamic naming and dedicated directory.

    Returns:
        dict: Container information including name and status
    """
    container_name = f"project-{user_id}-{project_id}"

    # Check if container already exists
    if _check_container_exists(container_name):
        raise Exception(f"Container {container_name} already exists")

    # Create dedicated project directory
    project_path = _create_project_directory(user_id, project_id)
    data_path = get_container_data_dir(user_id, project_id)
    data_path_abs = data_path.resolve()

    # Get the image name
    image_name = "steps-project"

    # Build docker run command with project-specific data directory
    docker_cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "--workdir",
        "/app",
        "-v",
        f"{data_path_abs}:/app",  # Mount project data directory
        "--restart",
        "unless-stopped",
    ]

    docker_cmd.append(image_name)

    result = _run_command(docker_cmd, capture_output=True, text=True, check=True)

    container_id = result.stdout.strip()

    # Copy container default files into the mounted directory
    project_root = Path(__file__).parent
    container_default_files_dir = project_root / "container_default_files"

    if container_default_files_dir.exists():
        # Copy all files from container_default_files directory to the mounted data directory
        for file_path in container_default_files_dir.iterdir():
            if file_path.is_file():
                dest_path = data_path_abs / file_path.name
                shutil.copy2(file_path, dest_path)

    # Create .cursor/rules and copy system_instruction/rules.mdc into it
    cursor_rules_dir = data_path_abs / ".cursor" / "rules"
    cursor_rules_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        project_root / "system_instruction" / "rules.mdc",
        cursor_rules_dir / "rules.mdc",
    )

    return {
        "status": "created",
        "container_name": container_name,
        "container_id": container_id,
        "project_dir": str(project_path),
        "data_dir": str(data_path_abs),
        "message": f"Container {container_name} created successfully. Data dir: {data_path_abs}",
    }


def remove_container(
    user_id: str,
    project_id: str,
    force: bool = False,
    remove_dir: bool = False,
) -> dict:
    """
    Remove a container and its project directory.

    Returns:
        dict: Removal status
    """
    container_name = f"project-{user_id}-{project_id}"
    project_path = _get_project_dir(user_id, project_id)

    # First, stop the container if it's running
    stop_cmd = ["docker", "stop", container_name]
    stop_result = _run_command(stop_cmd, capture_output=True, text=True)
    # Ignore errors if container is not running or doesn't exist

    # Then remove the container
    cmd = ["docker", "rm"]
    if force:
        cmd.append("-f")
    cmd.append(container_name)

    result = _run_command(cmd, capture_output=True, text=True, check=True)

    message = f"Container {container_name} removed successfully"

    # Remove project directory (default behavior)
    if remove_dir and project_path.exists():
        try:
            shutil.rmtree(project_path)
            message += f" and project directory {project_path} removed"
        except Exception as e:
            message += f" (but failed to remove directory: {str(e)})"

    return {
        "status": "removed",
        "container_name": container_name,
        "project_dir": str(project_path) if project_path.exists() else None,
        "message": message,
    }


def list_containers(user_id: str = None) -> list:
    """
    List all project containers or containers for a specific user

    Args:
        user_id: Optional user ID to filter containers

    Returns:
        list: List of container information
    """
    filter_name = f"project-{user_id}-" if user_id else "project-"

    result = _run_command(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"name={filter_name}",
            "--format",
            "{{.Names}}\t{{.Status}}\t{{.Image}}",
        ],
        capture_output=True,
        text=True,
    )

    containers = []
    for line in result.stdout.strip().split("\n"):
        if line:
            parts = line.split("\t")
            if len(parts) >= 2:
                containers.append(
                    {
                        "name": parts[0],
                        "status": parts[1],
                        "image": parts[2] if len(parts) > 2 else "",
                    }
                )

    return containers


def run_agent(
    user_id: str,
    project_id: str,
    prompt: str,
    resume_latest: bool = True,
    force: bool = True,
) -> dict:
    """
    Run cursor-agent with stream-json output

    Args:
        user_id: User identifier
        project_id: Project identifier
        prompt: Prompt for the agent
        resume_latest: If True, automatically resume the latest session from stream events files
        force: Force allow commands unless explicitly denied

    Returns:
        dict: Agent execution result with stream_events, final_result, and structured_output
    """
    container_name = f"project-{user_id}-{project_id}"

    api_key = settings.CURSOR_API_KEY
    if not api_key:
        raise Exception(
            "CURSOR_API_KEY not found in .env file. CURSOR_API_KEY is required. Please add it to .env file."
        )

    # Build cursor-agent command
    cmd = ["cursor-agent"]

    # Add session resume if provided
    session_id = None
    resume_session_id = None  # Store the session_id we're resuming (if any)
    if resume_latest:
        # Use a helper function to get the latest session id if exists
        resume_session_id = _get_latest_session_id(user_id, project_id)
        if resume_session_id:
            session_id = resume_session_id
            cmd.extend(["--resume", session_id])

    full_prompt = prompt
    cmd.extend(["-p", full_prompt])

    # Add force flag if provided
    if force:
        cmd.extend(["-f"])

    # Request stream-json output (newline-delimited JSON)
    cmd.extend(["--output-format", "stream-json"])

    # Build docker exec command with environment variable
    docker_cmd = [
        "docker",
        "exec",
        "-e",
        f"CURSOR_API_KEY={api_key}",
        container_name,
    ] + cmd

    result = _run_command(docker_cmd, capture_output=True, text=True, check=True)

    # Parse stream-json format (newline-delimited JSON)
    stream_events = []
    final_result = None

    for line in result.stdout.strip().split("\n"):
        if line.strip():
            event = json.loads(line)
            stream_events.append(event)
            # Extract final result if available
            if event.get("type") == "result":
                final_result = event
            # Extract session_id from stream events if available
            if not session_id and event.get("session_id"):
                session_id = event.get("session_id")

    # Extract session_id from final_result if not found in events
    if not session_id and final_result and final_result.get("session_id"):
        session_id = final_result.get("session_id")

    # Store conversation
    # Save stream events to file
    # File format: YYYYMMDD_HHMM_<session_id>_stream_events.jsonl
    project_dir = _get_project_dir(user_id, project_id)
    assert project_dir.exists()

    if not session_id:
        raise ValueError("session_id not found in cursor-agent response")

    # Check if we're resuming (session_id was set before running cursor-agent)
    is_resume = resume_session_id is not None and session_id == resume_session_id

    if is_resume:
        # Find existing file for this session_id
        existing_files = list(project_dir.glob(f"*_{session_id}_stream_events.jsonl"))
        if existing_files:
            # Use the existing file (should be only one)
            stream_events_file = existing_files[0]
        else:
            # Fallback: create new file if existing file not found
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            stream_events_file = (
                project_dir / f"{timestamp}_{session_id}_stream_events.jsonl"
            )
    else:
        # New session: create new file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        stream_events_file = (
            project_dir / f"{timestamp}_{session_id}_stream_events.jsonl"
        )

    with open(stream_events_file, "a") as f:
        for event in stream_events:
            f.write(json.dumps(event) + "\n")

    return {
        "status": "success",
        "stream_events": stream_events,
        "final_result": final_result,
        "structured_output": final_result,
    }


def get_latest_conversation(user_id: str, project_id: str) -> list:
    """
    Get conversation history for the latest session of a project.
    Returns a list of conversation turns, each containing user prompt and agent result.

    Args:
        user_id: User identifier
        project_id: Project identifier

    Returns:
        list: List of conversation turns from the latest session, each with:
            - timestamp: Timestamp of the conversation turn
            - session_id: Session ID
            - user_prompt: User's prompt (if available)
            - agent_result: Agent's final result (if available)
    """
    project_dir = _get_project_dir(user_id, project_id)
    if not project_dir.exists():
        return []

    # Get the latest session ID
    latest_session_id = _get_latest_session_id(user_id, project_id)
    if not latest_session_id:
        return []

    # Find all stream events files for the latest session
    # Pattern: YYYYMMDD_HHMM_<session_id>_stream_events.jsonl
    stream_files = list(project_dir.glob(f"*_{latest_session_id}_stream_events.jsonl"))
    if not stream_files:
        return []

    assert (
        len(stream_files) == 1
    ), f"Expected exactly one stream file for session {latest_session_id}, found {len(stream_files)}"
    stream_file = stream_files[0]

    # Parse filename: YYYYMMDD_HHMM_<session_id>_stream_events.jsonl
    parts = stream_file.stem.split("_")
    if len(parts) < 3:
        return []

    timestamp_str = f"{parts[0]}_{parts[1]}"
    session_id = parts[2]

    # Read all events from the file first
    events = []
    try:
        with open(stream_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        return []

    # Process events to extract conversation turns
    conversation_turns = []
    current_prompt = None

    for event in events:
        # Look for user message
        if event.get("type") == "user":
            message = event.get("message", {})
            content = message.get("content", [])
            if not content or len(content) == 0:
                continue
            text_content = content[0].get("text", "")
            if text_content:
                current_prompt = text_content
                # Remove system prompt if present (rough heuristic)
                if "# Instructions" in current_prompt:
                    # Find the last occurrence of double newline and take everything after it
                    # System prompt ends with "\n\n" followed by user's actual request
                    last_double_newline = current_prompt.rfind("\n\n")
                    if last_double_newline != -1:
                        # Take everything after the last double newline
                        user_part = current_prompt[last_double_newline + 2 :].strip()
                        if user_part:  # Only use if there's actual content
                            current_prompt = user_part

        # When we find a result, create a conversation turn with the preceding user prompt
        if event.get("type") == "result":
            agent_result = event.get("result", "")
            if current_prompt:
                conversation_turns.append(
                    {
                        "timestamp": timestamp_str,
                        "session_id": session_id,
                        "user_prompt": current_prompt,
                        "agent_result": agent_result,
                    }
                )
            # Reset prompt for next turn
            current_prompt = None

    return conversation_turns


def exec_command(user_id: str, project_id: str, command: list) -> dict:
    """
    Execute a command in a container

    Args:
        user_id: User identifier
        project_id: Project identifier
        command: Command to execute (as list)

    Returns:
        dict: Command execution result
    """
    container_name = f"project-{user_id}-{project_id}"

    docker_cmd = ["docker", "exec", container_name] + command

    result = _run_command(docker_cmd, capture_output=True, text=True, check=True)

    return {
        "status": "success",
        "container_name": container_name,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def get_dependencies(user_id: str, project_id: str) -> dict:
    """
    Get Python package dependencies from inside a container

    Args:
        user_id: User identifier
        project_id: Project identifier

    Returns:
        dict: Dependencies result with requirements.txt formatted output
    """
    container_name = f"project-{user_id}-{project_id}"

    if not _check_container_exists(container_name):
        raise Exception(f"Container {container_name} does not exist")

    if not _check_container_running(container_name):
        raise Exception(f"Container {container_name} exists but is not running")

    docker_cmd = ["docker", "exec", container_name, "pip", "freeze"]

    result = _run_command(docker_cmd, capture_output=True, text=True, check=True)

    return {
        "status": "success",
        "container_name": container_name,
        "dependencies": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def create_debug_process(
    user_id: str,
    project_id: str,
    code_file: str = "main.py",
) -> subprocess.Popen:
    container_name = f"project-{user_id}-{project_id}"
    command = f"docker exec -i {container_name} python -m pdb {code_file}".split()
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    return process
