import asyncio
import json
import logging
import uuid
from enum import Enum
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel

from resource_based_modules.database.core import DbSession
from resource_based_modules.project.models import Project
from resource_based_modules.project.schemas import (
    ProjectPaginationResponse,
    ProjectResponse,
)
from resource_based_modules import crud
from resource_based_modules.schema_base import PrimaryKey
from server.ws import manager
from settings import settings
from utils.llm import edit_code_with_llm, generate_code_with_llm
from utils.misc import get_function_ranges
from utils.syntax_highlight import get_python_highlights

logger = logging.getLogger(__name__)

router = APIRouter()


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


agent_tasks: Dict[str, Dict[str, Any]] = {}


class CodeOverwriteRequest(BaseModel):
    code: str


class CodeGenerationRequest(BaseModel):
    request: str


class CodeEditRequest(BaseModel):
    request: str
    selected_lines: str | None = None
    use_execution_history: bool = False
    session_id: str | None = None


class AgentRequest(BaseModel):
    prompt: str


async def _run_agent_background(
    task_id: str,
    user_id: str,
    project_id: str,
    prompt: str,
) -> None:
    """Background task to run agent and update task status."""
    import steps_project_engine

    agent_tasks[task_id]["status"] = TaskStatus.RUNNING

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            steps_project_engine.run_agent,
            user_id,
            project_id,
            prompt,
        )

        agent_tasks[task_id]["status"] = TaskStatus.COMPLETED
        agent_tasks[task_id]["result"] = result
        agent_tasks[task_id]["error"] = None

        message = {
            "type": "agent_result",
            "task_id": task_id,
            "status": "completed",
            "result": result,
        }
        await manager.send_to(project_id, json.dumps(message))

    except Exception as e:
        logger.error(
            f"Error running agent for project {project_id}: {e}", exc_info=True
        )
        agent_tasks[task_id]["status"] = TaskStatus.FAILED
        agent_tasks[task_id]["result"] = None
        agent_tasks[task_id]["error"] = str(e)

        message = {
            "type": "agent_result",
            "task_id": task_id,
            "status": "failed",
            "error": str(e),
        }
        await manager.send_to(project_id, json.dumps(message))


@router.get("/api/projects", response_model=ProjectPaginationResponse)
def get_projects(
    db_session: DbSession,
    page: int = 1,
    items_per_page: int = 20,
):
    """List projects with pagination (existence determined by DB row)."""
    total = db_session.query(Project).count()
    projects = (
        crud.get_all(db_session=db_session, model=Project)
        .order_by(Project.id)
        .offset((page - 1) * items_per_page)
        .limit(items_per_page)
        .all()
    )
    return ProjectPaginationResponse(
        itemsPerPage=items_per_page,
        page=page,
        total=total,
        items=[ProjectResponse.model_validate(p) for p in projects],
    )


@router.post("/api/projects", response_model=ProjectResponse)
async def create_project(db_session: DbSession):
    """Create a new project (DB row first, then Docker container)."""
    user_id = "1"
    project = crud.create(db_session=db_session, obj=Project(container_name=None))
    project_id_str = str(project.id)

    try:
        from steps_project_engine.manage import create_container

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            create_container,
            user_id,
            project_id_str,
        )
        project.container_name = result["container_name"]
        crud.update(
            db_session=db_session, db_obj=project, update_fields=["container_name"]
        )
        return project
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to create project: {str(e)}"
        )


@router.delete("/api/projects/{project_id}")
async def delete_project(db_session: DbSession, project_id: int):
    """Delete a project (DB row and Docker container/directory)."""
    user_id = "1"
    project = crud.get_by_id(db_session=db_session, model=Project, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    project_id_str = str(project_id)

    try:
        from steps_project_engine.manage import remove_container

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            remove_container,
            user_id,
            project_id_str,
            False,
            True,
        )
        crud.delete(db_session=db_session, obj=project)
        return {
            "id": project_id,
            "status": "deleted",
            "message": result["message"],
        }
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete project: {str(e)}"
        )


@router.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(db_session: DbSession, project_id: PrimaryKey):
    """Get a project by id (existence determined by DB row)."""
    project = crud.get_by_id(db_session=db_session, model=Project, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return project


@router.post("/api/projects/{project_id}/run_agent")
async def run_agent(
    db_session: DbSession,
    project_id: int,
    request: AgentRequest,
    background_tasks: BackgroundTasks,
):
    """
    Run cursor-agent in the project container with the given prompt.
    Returns immediately with a task_id. Results will be sent via WebSocket.
    """
    project = crud.get_by_id(db_session=db_session, model=Project, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    user_id = "1"
    project_id_str = str(project_id)
    task_id = str(uuid.uuid4())

    agent_tasks[task_id] = {
        "status": TaskStatus.PENDING,
        "project_id": project_id_str,
        "prompt": request.prompt,
        "result": None,
        "error": None,
    }

    background_tasks.add_task(
        _run_agent_background,
        task_id,
        user_id,
        project_id_str,
        request.prompt,
    )

    return {
        "task_id": task_id,
        "status": TaskStatus.PENDING,
        "message": "Agent task started. Results will be sent via WebSocket.",
    }


@router.get("/api/projects/{project_id}/conversation_history")
async def read_conversation_history(db_session: DbSession, project_id: int):
    """Read conversation history for a project."""
    project = crud.get_by_id(db_session=db_session, model=Project, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    import steps_project_engine

    user_id = "1"
    project_id_str = str(project_id)

    try:
        history = steps_project_engine.get_latest_conversation(
            user_id=user_id,
            project_id=project_id_str,
        )
        return {"conversation_history": history}
    except Exception as e:
        logger.error(
            f"Error getting conversation history for project {project_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get conversation history: {str(e)}"
        )


@router.post("/api/projects/{project_id}/code")
async def generate_and_save_code(
    db_session: DbSession, project_id: int, request: CodeGenerationRequest
):
    """Generate code based on user request and save it to the media directory."""
    project = crud.get_by_id(db_session=db_session, model=Project, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    file_path = (
        settings.PROJECT_CONTAINERS_DIR / "1" / str(project_id) / "data" / "main.py"
    )

    if file_path.exists():
        raise HTTPException(status_code=400, detail="main.py already exists")

    try:
        generated_code = generate_code_with_llm(request=request.request)
    except Exception as e:
        logger.error(f"Error generating code: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate code: {str(e)}"
        )

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(generated_code)
    return {"success": True}


# TODO maybe we should notify this to the agent too
@router.post("/api/projects/{project_id}/code/edit")
async def edit_and_save_code(
    db_session: DbSession, project_id: int, request: CodeEditRequest
):
    """Edit the existing code based on user request and save it to the media directory."""
    project = crud.get_by_id(db_session=db_session, model=Project, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    file_path = (
        settings.PROJECT_CONTAINERS_DIR / "1" / str(project_id) / "data" / "main.py"
    )

    if not file_path.exists():
        raise HTTPException(status_code=400, detail="main.py does not exist")

    with open(file_path) as f:
        code = f.read()

    execution_history = None
    if request.use_execution_history:
        raise HTTPException(
            status_code=400,
            detail="execution_history is not available without session mapping",
        )

    retry = 3
    edited_code = None
    while retry > 0:
        try:
            edited_code = edit_code_with_llm(
                code=code,
                request=request.request,
                selected_lines=request.selected_lines,
                execution_history=execution_history,
            )
            break
        except Exception as e:
            retry -= 1
            if retry == 0:
                logger.error(f"Error editing code: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to edit code: {str(e)}"
                )

    if edited_code is None:
        raise HTTPException(
            status_code=500, detail="Failed to edit code after all retries"
        )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(edited_code)

    return {"success": True}


@router.put("/api/projects/{project_id}/code")
async def overwrite_code(
    db_session: DbSession, project_id: int, request: CodeOverwriteRequest
):
    """
    Overwrite the code for a specific project with the provided code.
    Used for saving manual edits made by the user in the frontend editor.
    """
    project = crud.get_by_id(db_session=db_session, model=Project, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    file_path = (
        settings.PROJECT_CONTAINERS_DIR / "1" / str(project_id) / "data" / "main.py"
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"No code file found for project {project_id}"
        )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(request.code)

    return {"success": True}


@router.get("/api/projects/{project_id}/code")
def read_project_code(db_session: DbSession, project_id: int):
    """Read the generated code for a specific project."""
    project = crud.get_by_id(db_session=db_session, model=Project, id=project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    file_path = (
        settings.PROJECT_CONTAINERS_DIR / "1" / str(project_id) / "data" / "main.py"
    )

    if not file_path.exists():
        return {"content": "", "functions": [], "highlights": []}

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "content": content,
        "functions": get_function_ranges(content),
        "highlights": get_python_highlights(content),
    }
