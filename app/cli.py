import click
from sqlalchemy import inspect, text

from app import db
from app.models import Category, Project, Question, Todo, User


DEFAULT_CATEGORIES = [
    ("ERP", "#3b82f6"),
    ("SQL", "#10b981"),
    ("Python", "#6366f1"),
    ("AI", "#8b5cf6"),
    ("English", "#f59e0b"),
    ("Vietnam", "#ef4444"),
    ("MES", "#14b8a6"),
    ("WMS", "#06b6d4"),
    ("Others", "#64748b"),
]


def register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        click.echo("Database initialized.")

    @app.cli.command("upgrade-db")
    def upgrade_db():
        db.create_all()
        inspector = inspect(db.engine)
        todo_columns = {column["name"] for column in inspector.get_columns("todos")}
        if "project_id" not in todo_columns:
            db.session.execute(text("ALTER TABLE todos ADD COLUMN project_id INTEGER"))
            db.session.commit()
            click.echo("Added todos.project_id.")
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "is_active_flag" not in user_columns:
            db.session.execute(text("ALTER TABLE users ADD COLUMN is_active_flag BOOLEAN NOT NULL DEFAULT 1"))
            db.session.commit()
            click.echo("Added users.is_active_flag.")
        click.echo("Database schema is up to date.")

    @app.cli.command("seed")
    @click.option("--username", default="admin")
    @click.option("--password", default="admin123")
    def seed(username, password):
        db.create_all()

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, display_name="Allen Chen", is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
        else:
            user.is_admin = True
            user.is_active_flag = True

        for name, color in DEFAULT_CATEGORIES:
            exists = Category.query.filter_by(user_id=user.id, name=name).first()
            if not exists:
                db.session.add(Category(user_id=user.id, name=name, color=color))

        default_projects = [
            ("ERP 學習計畫", "ERP、MRP、採購與工作流程學習"),
            ("門禁系統 API", "門禁系統 API 修改、文件與測試"),
            ("SQL 能力提升", "SQL 查詢、Window Function 與效能練習"),
        ]
        for name, description in default_projects:
            exists = Project.query.filter_by(user_id=user.id, name=name).first()
            if not exists:
                db.session.add(Project(user_id=user.id, name=name, description=description))
        db.session.flush()

        projects = {project.name: project for project in Project.query.filter_by(user_id=user.id).all()}

        if not Todo.query.filter_by(user_id=user.id).first():
            db.session.add_all(
                [
                    Todo(user_id=user.id, project_id=projects["ERP 學習計畫"].id, title="學習 ERP 第5章：採購管理", priority="High", sort_order=1),
                    Todo(user_id=user.id, project_id=projects["門禁系統 API"].id, title="修改門禁系統 API", priority="High", sort_order=2),
                    Todo(user_id=user.id, project_id=projects["SQL 能力提升"].id, title="SQL 練習：Window Function", priority="Medium", sort_order=3),
                ]
            )
        else:
            project_by_title = {
                "學習 ERP 第5章：採購管理": "ERP 學習計畫",
                "修改門禁系統 API": "門禁系統 API",
                "SQL 練習：Window Function": "SQL 能力提升",
            }
            for title, project_name in project_by_title.items():
                todo = Todo.query.filter_by(user_id=user.id, title=title).first()
                if todo and not todo.project_id:
                    todo.project_id = projects[project_name].id

        if not Question.query.filter_by(user_id=user.id).first():
            db.session.add_all(
                [
                    Question(user_id=user.id, question="MRP 的 Planning Time Fence 是什麼？"),
                    Question(user_id=user.id, question="為什麼 SQL 執行計畫會影響查詢速度？"),
                ]
            )

        db.session.commit()
        click.echo(f"Seeded user: {username} / {password}")
