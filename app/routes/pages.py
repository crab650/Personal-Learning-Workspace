import markdown
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app import db
from app.models import Category, Note, Project, Question, StoredFile, Tag, Todo, User, utc_now


pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return render_template("landing.html")


@pages_bp.route("/dashboard")
@login_required
def dashboard():
    user_id = current_user.id
    return render_template(
        "dashboard.html",
        active_page="dashboard",
        notes=Note.query.filter_by(user_id=user_id).order_by(Note.updated_at.desc()).limit(5).all(),
        questions=Question.query.filter_by(user_id=user_id).order_by(Question.updated_at.desc()).limit(5).all(),
        todos=Todo.query.filter_by(user_id=user_id).order_by(Todo.sort_order.asc(), Todo.created_at.desc()).limit(6).all(),
        files=StoredFile.query.filter_by(user_id=user_id).order_by(StoredFile.updated_at.desc()).limit(5).all(),
    )


@pages_bp.route("/notes")
@login_required
def notes():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    query = Note.query.filter_by(user_id=current_user.id)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Note.title.ilike(like), Note.markdown_content.ilike(like)))
    if category_id:
        query = query.filter_by(category_id=category_id)

    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    notes = query.order_by(Note.updated_at.desc()).all()
    return render_template(
        "notes/list.html",
        title="學習筆記",
        active_page="notes",
        notes=notes,
        categories=categories,
        selected_category_id=category_id,
        q=q,
    )


@pages_bp.route("/notes/new", methods=["GET", "POST"])
@login_required
def note_new():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    if request.method == "POST":
        note = Note(user_id=current_user.id)
        _populate_note_from_form(note)
        db.session.add(note)
        db.session.commit()
        return redirect(url_for("pages.note_detail", note_id=note.id))

    return render_template(
        "notes/form.html",
        title="新增筆記",
        active_page="notes",
        note=None,
        categories=categories,
        tag_text="",
    )


@pages_bp.route("/notes/<int:note_id>")
@login_required
def note_detail(note_id):
    note = _get_user_note(note_id)
    rendered_html = _render_markdown(note.markdown_content)
    return render_template(
        "notes/detail.html",
        title=note.title,
        active_page="notes",
        note=note,
        rendered_html=rendered_html,
    )


@pages_bp.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def note_edit(note_id):
    note = _get_user_note(note_id)
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    if request.method == "POST":
        _populate_note_from_form(note)
        db.session.commit()
        return redirect(url_for("pages.note_detail", note_id=note.id))

    return render_template(
        "notes/form.html",
        title="編輯筆記",
        active_page="notes",
        note=note,
        categories=categories,
        tag_text=", ".join(tag.name for tag in note.tags),
    )


@pages_bp.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def note_delete(note_id):
    note = _get_user_note(note_id)
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for("pages.notes"))


@pages_bp.route("/todos")
@login_required
def todos():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()
    category_id = request.args.get("category_id", type=int)
    project_id = request.args.get("project_id", type=int)
    group_by = request.args.get("group_by", "status")
    if group_by not in {"status", "category", "project"}:
        group_by = "status"
    query = Todo.query.filter_by(user_id=current_user.id)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Todo.title.ilike(like), Todo.description.ilike(like)))
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if project_id:
        query = query.filter_by(project_id=project_id)

    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.name).all()
    todos = query.order_by(Todo.status.asc(), Todo.sort_order.asc(), Todo.created_at.desc()).all()
    groups = _todo_groups(todos, group_by, categories, projects)
    rendered_descriptions = {
        todo.id: _render_markdown(todo.description)
        for todo in todos
        if todo.description
    }
    return render_template(
        "todos/list.html",
        title="待辦事項",
        active_page="todos",
        todos=todos,
        groups=groups,
        categories=categories,
        projects=projects,
        selected_status=status,
        selected_priority=priority,
        selected_category_id=category_id,
        selected_project_id=project_id,
        group_by=group_by,
        q=q,
        statuses=["Todo", "Doing", "Done", "Cancel"],
        priorities=["High", "Medium", "Low"],
        rendered_descriptions=rendered_descriptions,
    )


@pages_bp.route("/todos/new", methods=["GET", "POST"])
@login_required
def todo_new():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.name).all()
    if request.method == "POST":
        todo = Todo(user_id=current_user.id)
        _populate_todo_from_form(todo)
        max_order = (
            db.session.query(db.func.max(Todo.sort_order))
            .filter_by(user_id=current_user.id, status=todo.status)
            .scalar()
            or 0
        )
        todo.sort_order = max_order + 1
        db.session.add(todo)
        db.session.commit()
        return redirect(url_for("pages.todos"))

    return render_template(
        "todos/form.html",
        title="新增待辦",
        active_page="todos",
        todo=None,
        categories=categories,
        projects=projects,
        statuses=["Todo", "Doing", "Done", "Cancel"],
        priorities=["High", "Medium", "Low"],
    )


@pages_bp.route("/todos/<int:todo_id>/edit", methods=["GET", "POST"])
@login_required
def todo_edit(todo_id):
    todo = _get_user_todo(todo_id)
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    projects = Project.query.filter_by(user_id=current_user.id).order_by(Project.name).all()
    if request.method == "POST":
        _populate_todo_from_form(todo)
        db.session.commit()
        return redirect(url_for("pages.todos"))

    return render_template(
        "todos/form.html",
        title="編輯待辦",
        active_page="todos",
        todo=todo,
        categories=categories,
        projects=projects,
        statuses=["Todo", "Doing", "Done", "Cancel"],
        priorities=["High", "Medium", "Low"],
    )


@pages_bp.route("/todos/<int:todo_id>/delete", methods=["POST"])
@login_required
def todo_delete(todo_id):
    todo = _get_user_todo(todo_id)
    db.session.delete(todo)
    db.session.commit()
    return redirect(url_for("pages.todos"))


@pages_bp.route("/todos/<int:todo_id>/status", methods=["POST"])
@login_required
def todo_status(todo_id):
    todo = _get_user_todo(todo_id)
    status = request.form.get("status", "Todo")
    if status not in {"Todo", "Doing", "Done", "Cancel"}:
        abort(400)
    _set_todo_status(todo, status)
    db.session.commit()
    return redirect(request.referrer or url_for("pages.todos"))


@pages_bp.route("/projects")
@login_required
def projects():
    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()
    query = Project.query.filter_by(user_id=current_user.id)
    if status:
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Project.name.ilike(like), Project.description.ilike(like)))

    projects = query.order_by(Project.updated_at.desc()).all()
    todo_counts = {
        project.id: Todo.query.filter_by(user_id=current_user.id, project_id=project.id).count()
        for project in projects
    }
    return render_template(
        "projects/list.html",
        title="專案管理",
        active_page="projects",
        projects=projects,
        todo_counts=todo_counts,
        selected_status=status,
        q=q,
        statuses=["Active", "Paused", "Done", "Archived"],
    )


@pages_bp.route("/projects/new", methods=["GET", "POST"])
@login_required
def project_new():
    error = None
    if request.method == "POST":
        project = Project(user_id=current_user.id)
        error = _populate_project_from_form(project)
        if not error:
            db.session.add(project)
            db.session.commit()
            return redirect(url_for("pages.project_detail", project_id=project.id))

    return render_template(
        "projects/form.html",
        title="新增專案",
        active_page="projects",
        project=None,
        statuses=["Active", "Paused", "Done", "Archived"],
        error=error,
    )


@pages_bp.route("/projects/<int:project_id>")
@login_required
def project_detail(project_id):
    project = _get_user_project(project_id)
    todos = (
        Todo.query.filter_by(user_id=current_user.id, project_id=project.id)
        .order_by(Todo.status.asc(), Todo.sort_order.asc(), Todo.updated_at.desc())
        .all()
    )
    rendered_descriptions = {
        todo.id: _render_markdown(todo.description)
        for todo in todos
        if todo.description
    }
    return render_template(
        "projects/detail.html",
        title=project.name,
        active_page="projects",
        project=project,
        todos=todos,
        rendered_descriptions=rendered_descriptions,
    )


@pages_bp.route("/projects/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def project_edit(project_id):
    project = _get_user_project(project_id)
    error = None
    if request.method == "POST":
        error = _populate_project_from_form(project)
        if not error:
            db.session.commit()
            return redirect(url_for("pages.project_detail", project_id=project.id))

    return render_template(
        "projects/form.html",
        title="編輯專案",
        active_page="projects",
        project=project,
        statuses=["Active", "Paused", "Done", "Archived"],
        error=error,
    )


@pages_bp.route("/projects/<int:project_id>/delete", methods=["POST"])
@login_required
def project_delete(project_id):
    project = _get_user_project(project_id)
    Todo.query.filter_by(user_id=current_user.id, project_id=project.id).update({"project_id": None})
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for("pages.projects"))


@pages_bp.route("/questions")
@login_required
def questions():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    category_id = request.args.get("category_id", type=int)
    understood = request.args.get("understood", "").strip()
    completed = request.args.get("completed", "").strip()
    query = Question.query.filter_by(user_id=current_user.id)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Question.question.ilike(like), Question.gpt_answer.ilike(like)))
    if status:
        query = query.filter_by(status=status)
    if category_id:
        query = query.filter_by(category_id=category_id)
    if understood in {"yes", "no"}:
        query = query.filter_by(is_understood=(understood == "yes"))
    if completed in {"yes", "no"}:
        query = query.filter_by(is_completed=(completed == "yes"))

    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    questions = query.order_by(Question.updated_at.desc()).all()
    rendered_answers = {
        question.id: _render_markdown(question.gpt_answer)
        for question in questions
        if question.gpt_answer
    }
    return render_template(
        "questions/list.html",
        title="問題池",
        active_page="questions",
        questions=questions,
        categories=categories,
        q=q,
        selected_status=status,
        selected_category_id=category_id,
        selected_understood=understood,
        selected_completed=completed,
        statuses=["Open", "Reviewing", "Answered", "Closed"],
        rendered_answers=rendered_answers,
    )


@pages_bp.route("/questions/new", methods=["GET", "POST"])
@login_required
def question_new():
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    if request.method == "POST":
        question = Question(user_id=current_user.id)
        _populate_question_from_form(question)
        db.session.add(question)
        db.session.commit()
        return redirect(url_for("pages.question_detail", question_id=question.id))

    return render_template(
        "questions/form.html",
        title="新增問題",
        active_page="questions",
        question_item=None,
        categories=categories,
        statuses=["Open", "Reviewing", "Answered", "Closed"],
    )


@pages_bp.route("/questions/<int:question_id>")
@login_required
def question_detail(question_id):
    question = _get_user_question(question_id)
    rendered_answer = _render_markdown(question.gpt_answer)
    return render_template(
        "questions/detail.html",
        title="問題閱讀",
        active_page="questions",
        question_item=question,
        rendered_answer=rendered_answer,
    )


@pages_bp.route("/questions/<int:question_id>/edit", methods=["GET", "POST"])
@login_required
def question_edit(question_id):
    question = _get_user_question(question_id)
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    if request.method == "POST":
        _populate_question_from_form(question)
        db.session.commit()
        return redirect(url_for("pages.question_detail", question_id=question.id))

    return render_template(
        "questions/form.html",
        title="編輯問題",
        active_page="questions",
        question_item=question,
        categories=categories,
        statuses=["Open", "Reviewing", "Answered", "Closed"],
    )


@pages_bp.route("/questions/<int:question_id>/delete", methods=["POST"])
@login_required
def question_delete(question_id):
    question = _get_user_question(question_id)
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for("pages.questions"))


@pages_bp.route("/questions/<int:question_id>/toggle", methods=["POST"])
@login_required
def question_toggle(question_id):
    question = _get_user_question(question_id)
    field = request.form.get("field", "")
    if field == "understood":
        question.is_understood = not question.is_understood
    elif field == "completed":
        question.is_completed = not question.is_completed
        question.status = "Closed" if question.is_completed else "Open"
    else:
        abort(400)
    db.session.commit()
    return redirect(request.referrer or url_for("pages.questions"))


@pages_bp.route("/files")
@login_required
def files():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    query = StoredFile.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(StoredFile.original_name.ilike(f"%{q}%"))
    if category_id:
        query = query.filter_by(category_id=category_id)

    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    files = query.order_by(StoredFile.updated_at.desc()).all()
    return render_template(
        "files/list.html",
        title="檔案管理",
        active_page="files",
        files=files,
        categories=categories,
        selected_category_id=category_id,
        q=q,
    )


@pages_bp.route("/files/upload", methods=["POST"])
@login_required
def file_upload():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return redirect(url_for("pages.files"))

    upload_dir = _user_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    original_name = upload.filename
    safe_name = secure_filename(original_name) or "uploaded_file"
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    target = upload_dir / stored_name
    upload.save(target)

    stored_file = StoredFile(
        user_id=current_user.id,
        category_id=request.form.get("category_id", type=int) or None,
        original_name=original_name,
        stored_name=stored_name,
        content_type=upload.mimetype,
        size_bytes=target.stat().st_size,
    )
    db.session.add(stored_file)
    db.session.commit()
    return redirect(url_for("pages.files"))


@pages_bp.route("/files/<int:file_id>/download")
@login_required
def file_download(file_id):
    stored_file = _get_user_file(file_id)
    stored_file.download_count += 1
    db.session.commit()
    return send_from_directory(
        _user_upload_dir(),
        stored_file.stored_name,
        as_attachment=True,
        download_name=stored_file.original_name,
    )


@pages_bp.route("/files/<int:file_id>/view")
@login_required
def file_view(file_id):
    stored_file = _get_user_file(file_id)
    if not _is_markdown_file(stored_file.original_name):
        return redirect(url_for("pages.file_download", file_id=file_id))

    path = _user_upload_dir() / stored_file.stored_name
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="utf-8", errors="replace")
    rendered_html = _render_markdown(content)
    return render_template(
        "files/view.html",
        title=stored_file.original_name,
        active_page="files",
        file=stored_file,
        rendered_html=rendered_html,
        markdown_content=content,
    )


@pages_bp.route("/files/<int:file_id>/delete", methods=["POST"])
@login_required
def file_delete(file_id):
    stored_file = _get_user_file(file_id)
    path = _user_upload_dir() / stored_file.stored_name
    if path.exists():
        path.unlink()
    db.session.delete(stored_file)
    db.session.commit()
    return redirect(url_for("pages.files"))


@pages_bp.route("/search")
@login_required
def search():
    q = request.args.get("q", "").strip()
    results = {"notes": [], "todos": [], "projects": [], "questions": [], "files": []}

    if q:
        like = f"%{q}%"
        user_id = current_user.id
        results["notes"] = (
            Note.query.filter(
                Note.user_id == user_id,
                or_(Note.title.ilike(like), Note.markdown_content.ilike(like)),
            )
            .order_by(Note.updated_at.desc())
            .limit(20)
            .all()
        )
        results["todos"] = (
            Todo.query.filter(
                Todo.user_id == user_id,
                or_(Todo.title.ilike(like), Todo.description.ilike(like)),
            )
            .order_by(Todo.updated_at.desc())
            .limit(20)
            .all()
        )
        results["questions"] = (
            Question.query.filter(
                Question.user_id == user_id,
                or_(Question.question.ilike(like), Question.gpt_answer.ilike(like)),
            )
            .order_by(Question.updated_at.desc())
            .limit(20)
            .all()
        )
        results["projects"] = (
            Project.query.filter(
                Project.user_id == user_id,
                or_(Project.name.ilike(like), Project.description.ilike(like)),
            )
            .order_by(Project.updated_at.desc())
            .limit(20)
            .all()
        )
        results["files"] = (
            StoredFile.query.filter(
                StoredFile.user_id == user_id,
                StoredFile.original_name.ilike(like),
            )
            .order_by(StoredFile.updated_at.desc())
            .limit(20)
            .all()
        )

    total_count = sum(len(items) for items in results.values())
    return render_template(
        "search/results.html",
        title="全站搜尋",
        active_page="search",
        q=q,
        results=results,
        total_count=total_count,
    )


@pages_bp.route("/settings")
@login_required
def settings():
    return redirect(url_for("pages.users"))


@pages_bp.route("/settings/users")
@login_required
def users():
    _require_admin()
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template(
        "settings/users.html",
        title="使用者管理",
        active_page="settings",
        users=users,
    )


@pages_bp.route("/settings/users/new", methods=["GET", "POST"])
@login_required
def user_new():
    _require_admin()
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        display_name = request.form.get("display_name", "").strip() or username
        password = request.form.get("password", "")
        if not username or not password:
            error = "帳號與密碼必填"
        elif User.query.filter_by(username=username).first():
            error = "帳號已存在"
        else:
            user = User(
                username=username,
                display_name=display_name,
                is_admin=request.form.get("is_admin") == "on",
                is_active_flag=request.form.get("is_active_flag") == "on",
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("pages.users"))

    return render_template(
        "settings/user_form.html",
        title="新增使用者",
        active_page="settings",
        user_item=None,
        error=error,
    )


@pages_bp.route("/settings/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def user_edit(user_id):
    _require_admin()
    user = _get_user(user_id)
    error = None
    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        if not display_name:
            error = "顯示名稱必填"
        else:
            user.display_name = display_name
            user.is_admin = request.form.get("is_admin") == "on"
            user.is_active_flag = request.form.get("is_active_flag") == "on"
            if user.id == current_user.id:
                user.is_admin = True
                user.is_active_flag = True
            if password:
                user.set_password(password)
            db.session.commit()
            return redirect(url_for("pages.users"))

    return render_template(
        "settings/user_form.html",
        title="編輯使用者",
        active_page="settings",
        user_item=user,
        error=error,
    )


@pages_bp.route("/settings/users/<int:user_id>/toggle", methods=["POST"])
@login_required
def user_toggle(user_id):
    _require_admin()
    user = _get_user(user_id)
    if user.id != current_user.id:
        user.is_active_flag = not user.is_active_flag
        db.session.commit()
    return redirect(url_for("pages.users"))


def _render_markdown(content):
    return markdown.markdown(
        content or "",
        extensions=["extra", "fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )


def _require_admin():
    if not current_user.is_admin:
        abort(403)


def _get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    return user


def _get_user_note(note_id):
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first()
    if not note:
        abort(404)
    return note


def _get_user_todo(todo_id):
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
    if not todo:
        abort(404)
    return todo


def _get_user_project(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        abort(404)
    return project


def _get_user_question(question_id):
    question = Question.query.filter_by(id=question_id, user_id=current_user.id).first()
    if not question:
        abort(404)
    return question


def _get_user_file(file_id):
    stored_file = StoredFile.query.filter_by(id=file_id, user_id=current_user.id).first()
    if not stored_file:
        abort(404)
    return stored_file


def _user_upload_dir():
    return Path(current_app.config["UPLOAD_FOLDER"]) / f"user_{current_user.id}"


def _is_markdown_file(filename):
    return Path(filename).suffix.lower() in {".md", ".markdown", ".txt"}


def _populate_note_from_form(note):
    note.title = request.form.get("title", "").strip() or "未命名筆記"
    note.markdown_content = request.form.get("markdown_content", "")
    note.category_id = request.form.get("category_id", type=int) or None
    note.is_favorite = request.form.get("is_favorite") == "on"
    note.tags = _tags_from_text(request.form.get("tags", ""))


def _populate_todo_from_form(todo):
    todo.title = request.form.get("title", "").strip() or "未命名待辦"
    todo.description = request.form.get("description", "")
    todo.category_id = request.form.get("category_id", type=int) or None
    todo.project_id = _project_id_from_form()
    todo.priority = request.form.get("priority", "Medium")
    _set_todo_status(todo, request.form.get("status", "Todo"))
    todo.due_date = _parse_date(request.form.get("due_date", ""))
    todo.reminder_at = _parse_datetime(request.form.get("reminder_at", ""))


def _populate_project_from_form(project):
    name = request.form.get("name", "").strip()
    if not name:
        return "專案名稱必填"

    exists = Project.query.filter(
        Project.user_id == current_user.id,
        Project.name == name,
        Project.id != (project.id or 0),
    ).first()
    if exists:
        return "專案名稱已存在"

    project.name = name
    project.description = request.form.get("description", "")
    project.status = request.form.get("status", "Active")
    if project.status not in {"Active", "Paused", "Done", "Archived"}:
        project.status = "Active"
    return None


def _populate_question_from_form(question):
    question.question = request.form.get("question", "").strip() or "未命名問題"
    question.gpt_answer = request.form.get("gpt_answer", "")
    question.category_id = request.form.get("category_id", type=int) or None
    question.status = request.form.get("status", "Open")
    question.is_understood = request.form.get("is_understood") == "on"
    question.is_completed = request.form.get("is_completed") == "on"
    if question.is_completed:
        question.status = "Closed"


def _set_todo_status(todo, status):
    old_status = todo.status
    todo.status = status
    if status == "Done" and old_status != "Done":
        todo.completed_at = utc_now()
    elif status != "Done":
        todo.completed_at = None


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_datetime(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M")


def _project_id_from_form():
    new_project_name = request.form.get("new_project_name", "").strip()
    if new_project_name:
        project = Project.query.filter_by(user_id=current_user.id, name=new_project_name).first()
        if not project:
            project = Project(user_id=current_user.id, name=new_project_name)
            db.session.add(project)
            db.session.flush()
        return project.id
    return request.form.get("project_id", type=int) or None


def _todo_groups(todos, group_by, categories, projects):
    if group_by == "category":
        groups = [
            {"title": category.name, "todos": [todo for todo in todos if todo.category_id == category.id]}
            for category in categories
        ]
        groups.append({"title": "未分類", "todos": [todo for todo in todos if not todo.category_id]})
        return groups

    if group_by == "project":
        groups = [
            {"title": project.name, "todos": [todo for todo in todos if todo.project_id == project.id]}
            for project in projects
        ]
        groups.append({"title": "未指定專案", "todos": [todo for todo in todos if not todo.project_id]})
        return groups

    return [
        {"title": status, "todos": [todo for todo in todos if todo.status == status]}
        for status in ["Todo", "Doing", "Done", "Cancel"]
    ]


def _tags_from_text(tag_text):
    names = []
    for raw_name in tag_text.replace("，", ",").split(","):
        name = raw_name.strip()
        if name and name not in names:
            names.append(name)

    tags = []
    for name in names:
        tag = Tag.query.filter_by(user_id=current_user.id, name=name).first()
        if not tag:
            tag = Tag(user_id=current_user.id, name=name)
            db.session.add(tag)
        tags.append(tag)
    return tags
