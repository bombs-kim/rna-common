"""Reset dev DB: drop tables, recreate, and seed test projects. Run from backend: uv run python reset_dev_db.py."""

from resource_based_modules.database.core import Base, engine, get_session
from resource_based_modules.project.models import Project


def main():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with get_session() as session:
        session.add_all(
            [
                Project(container_name="project-1-1"),
                Project(container_name="project-1-2"),
                Project(container_name="project-1-3"),
            ]
        )
    print("Reset DB and seeded 3 projects.")


if __name__ == "__main__":
    main()
