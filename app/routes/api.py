import uuid
from pathlib import Path
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app import db
from app.models import Category, Note, Project, Question, StoredFile, Tag, Todo, utc_now


api_bp = Blueprint("api", __name__)


def user_upload_dir():
    return Path(current_app.config["UPLOAD_FOLDER"]) / f"user_{current_user.id}"


def get_user_file(file_id):
    return StoredFile.query.filter_by(id=file_id, user_id=current_user.id).first()


def serialize_file(stored_file):
    return {
        "id": stored_file.id,
        "original_name": stored_file.original_name,
        "content_type": stored_file.content_type,
        "category": stored_file.category.name if stored_file.category else None,
        "category_id": stored_file.category_id,
        "size_bytes": stored_file.size_bytes,
        "download_count": stored_file.download_count,
        "created_at": stored_file.created_at.isoformat() if stored_file.created_at else None,
        "updated_at": stored_file.updated_at.isoformat() if stored_file.updated_at else None,
    }


def serialize_project(project):
    todo_count = Todo.query.filter_by(user_id=current_user.id, project_id=project.id).count()
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "todo_count": todo_count,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }


def get_user_project(project_id):
    return Project.query.filter_by(id=project_id, user_id=current_user.id).first()


def apply_project_payload(project, payload, partial=False):
    if not partial or "name" in payload:
        name = str(payload.get("name", "")).strip()
        if not name:
            return "name is required"
        exists = Project.query.filter(
            Project.user_id == current_user.id,
            Project.name == name,
            Project.id != (project.id or 0),
        ).first()
        if exists:
            return "name already exists"
        project.name = name
    if "description" in payload or not partial:
        project.description = payload.get("description", "")
    if "status" in payload or not partial:
        status = payload.get("status", "Active")
        if status not in {"Active", "Paused", "Done", "Archived"}:
            return "invalid status"
        project.status = status
    project.updated_at = utc_now()
    return None


def serialize_todo(todo):
    return {
        "id": todo.id,
        "title": todo.title,
        "created_by_name": todo.created_by_name,
        "description": todo.description,
        "category": todo.category.name if todo.category else None,
        "category_id": todo.category_id,
        "project": todo.project.name if todo.project else None,
        "project_id": todo.project_id,
        "priority": todo.priority,
        "status": todo.status,
        "sort_order": todo.sort_order,
        "due_date": todo.due_date.isoformat() if todo.due_date else None,
        "reminder_at": todo.reminder_at.isoformat() if todo.reminder_at else None,
        "completed_at": todo.completed_at.isoformat() if todo.completed_at else None,
        "created_at": todo.created_at.isoformat() if todo.created_at else None,
        "updated_at": todo.updated_at.isoformat() if todo.updated_at else None,
    }


def serialize_note(note, include_content=False):
    data = {
        "id": note.id,
        "title": note.title,
        "category": note.category.name if note.category else None,
        "category_id": note.category_id,
        "tags": [tag.name for tag in note.tags],
        "is_favorite": note.is_favorite,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }
    if include_content:
        data["markdown_content"] = note.markdown_content
    return data


def tags_from_payload(tag_names):
    tags = []
    if not isinstance(tag_names, list):
        return tags

    seen = set()
    for raw_name in tag_names:
        name = str(raw_name).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        tag = Tag.query.filter_by(user_id=current_user.id, name=name).first()
        if not tag:
            tag = Tag(user_id=current_user.id, name=name)
            db.session.add(tag)
        tags.append(tag)
    return tags


def get_user_note(note_id):
    return Note.query.filter_by(id=note_id, user_id=current_user.id).first()


def get_user_todo(todo_id):
    return Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()


def get_user_question(question_id):
    return Question.query.filter_by(id=question_id, user_id=current_user.id).first()


def serialize_question(question):
    return {
        "id": question.id,
        "question": question.question,
        "gpt_answer": question.gpt_answer,
        "category": question.category.name if question.category else None,
        "category_id": question.category_id,
        "status": question.status,
        "is_understood": question.is_understood,
        "is_completed": question.is_completed,
        "created_at": question.created_at.isoformat() if question.created_at else None,
        "updated_at": question.updated_at.isoformat() if question.updated_at else None,
    }


def apply_question_payload(question, payload, partial=False):
    if not partial or "question" in payload:
        text = str(payload.get("question", "")).strip()
        if not text:
            return "question is required"
        question.question = text
    if "gpt_answer" in payload or not partial:
        question.gpt_answer = payload.get("gpt_answer", "")
    if "status" in payload or not partial:
        status = payload.get("status", "Open")
        if status not in {"Open", "Reviewing", "Answered", "Closed"}:
            return "invalid status"
        question.status = status
    if "category_id" in payload:
        category_id = payload.get("category_id")
        if category_id:
            category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
            if not category:
                return "category not found"
        question.category_id = category_id or None
    elif not partial:
        question.category_id = None
    if "is_understood" in payload:
        question.is_understood = bool(payload.get("is_understood"))
    elif not partial:
        question.is_understood = False
    if "is_completed" in payload:
        question.is_completed = bool(payload.get("is_completed"))
    elif not partial:
        question.is_completed = False
    if question.is_completed:
        question.status = "Closed"
    question.updated_at = utc_now()
    return None


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_datetime(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def set_todo_status(todo, status):
    old_status = todo.status
    todo.status = status
    if status == "Done" and old_status != "Done":
        todo.completed_at = utc_now()
    elif status != "Done":
        todo.completed_at = None


def apply_todo_payload(todo, payload, partial=False):
    if not partial or "title" in payload:
        title = str(payload.get("title", "")).strip()
        if not title:
            return "title is required"
        todo.title = title

    if "description" in payload or not partial:
        todo.description = payload.get("description", "")
    if "priority" in payload or not partial:
        priority = payload.get("priority", "Medium")
        if priority not in {"High", "Medium", "Low"}:
            return "invalid priority"
        todo.priority = priority
    if "status" in payload or not partial:
        status = payload.get("status", "Todo")
        if status not in {"Todo", "Doing", "Done", "Cancel"}:
            return "invalid status"
        set_todo_status(todo, status)
    if "category_id" in payload:
        category_id = payload.get("category_id")
        if category_id:
            category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
            if not category:
                return "category not found"
        todo.category_id = category_id or None
    elif not partial:
        todo.category_id = None
    if "project_name" in payload and str(payload.get("project_name", "")).strip():
        project_name = str(payload.get("project_name", "")).strip()
        project = Project.query.filter_by(user_id=current_user.id, name=project_name).first()
        if not project:
            project = Project(user_id=current_user.id, name=project_name)
            db.session.add(project)
            db.session.flush()
        todo.project_id = project.id
    elif "project_id" in payload:
        project_id = payload.get("project_id")
        if project_id:
            project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
            if not project:
                return "project not found"
        todo.project_id = project_id or None
    elif not partial:
        todo.project_id = None
    if "due_date" in payload or not partial:
        todo.due_date = parse_date(payload.get("due_date"))
    if "reminder_at" in payload or not partial:
        todo.reminder_at = parse_datetime(payload.get("reminder_at"))

    todo.updated_at = utc_now()
    return None


@api_bp.get("/dashboard/stats")
@login_required
def dashboard_stats():
    user_id = current_user.id
    total_notes = Note.query.filter_by(user_id=user_id).count()
    todo_count = Todo.query.filter_by(user_id=user_id).count()
    done_count = Todo.query.filter_by(user_id=user_id, status="Done").count()
    question_count = Question.query.filter_by(user_id=user_id).count()
    open_question_count = Question.query.filter_by(user_id=user_id, is_completed=False).count()

    return jsonify(
        {
            "total_notes": total_notes,
            "todo_count": todo_count,
            "done_count": done_count,
            "question_count": question_count,
            "open_question_count": open_question_count,
        }
    )


@api_bp.get("/notes")
@login_required
def list_notes():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    query = Note.query.filter_by(user_id=current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Note.title.ilike(like),
                Note.markdown_content.ilike(like),
                Note.tags.any(Tag.name.ilike(like)),
            )
        )
    if category_id:
        query = query.filter_by(category_id=category_id)
    notes = query.order_by(Note.updated_at.desc()).all()
    return jsonify([serialize_note(note) for note in notes])


@api_bp.post("/notes")
@login_required
def create_note():
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    category_id = payload.get("category_id")
    if category_id:
        category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
        if not category:
            return jsonify({"error": "category not found"}), 404

    note = Note(
        user_id=current_user.id,
        title=title,
        markdown_content=payload.get("markdown_content", ""),
        category_id=category_id or None,
        is_favorite=bool(payload.get("is_favorite", False)),
    )
    note.tags = tags_from_payload(payload.get("tags", []))
    db.session.add(note)
    db.session.commit()
    return jsonify(serialize_note(note, include_content=True)), 201


@api_bp.get("/notes/<int:note_id>")
@login_required
def get_note(note_id):
    note = get_user_note(note_id)
    if not note:
        return jsonify({"error": "note not found"}), 404
    return jsonify(serialize_note(note, include_content=True))


@api_bp.put("/notes/<int:note_id>")
@login_required
def update_note(note_id):
    note = get_user_note(note_id)
    if not note:
        return jsonify({"error": "note not found"}), 404

    payload = request.get_json(silent=True) or {}
    if "title" in payload:
        title = str(payload.get("title", "")).strip()
        if not title:
            return jsonify({"error": "title is required"}), 400
        note.title = title
    if "markdown_content" in payload:
        note.markdown_content = payload.get("markdown_content", "")
    if "category_id" in payload:
        category_id = payload.get("category_id")
        if category_id:
            category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
            if not category:
                return jsonify({"error": "category not found"}), 404
        note.category_id = category_id or None
    if "is_favorite" in payload:
        note.is_favorite = bool(payload.get("is_favorite"))
    if "tags" in payload:
        note.tags = tags_from_payload(payload.get("tags", []))

    note.updated_at = utc_now()
    db.session.commit()
    return jsonify(serialize_note(note, include_content=True))


@api_bp.delete("/notes/<int:note_id>")
@login_required
def delete_note(note_id):
    note = get_user_note(note_id)
    if not note:
        return jsonify({"error": "note not found"}), 404
    note_image_dir = (
        Path(current_app.config["UPLOAD_FOLDER"])
        / "note_images"
        / f"user_{current_user.id}"
    )
    for image in list(note.images):
        (note_image_dir / image.stored_name).unlink(missing_ok=True)
    db.session.delete(note)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/todos")
@login_required
def list_todos():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    priority = request.args.get("priority", "").strip()
    project_id = request.args.get("project_id", type=int)
    query = Todo.query.filter_by(user_id=current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Todo.title.ilike(like), Todo.description.ilike(like)))
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if project_id:
        query = query.filter_by(project_id=project_id)
    todos = query.order_by(Todo.status.asc(), Todo.sort_order.asc(), Todo.created_at.desc()).all()
    return jsonify([serialize_todo(todo) for todo in todos])


@api_bp.post("/todos")
@login_required
def create_todo():
    payload = request.get_json(silent=True) or {}
    todo = Todo(user_id=current_user.id)
    todo.created_by_name = current_user.display_name
    error = apply_todo_payload(todo, payload, partial=False)
    if error:
        status = 404 if error in {"category not found", "project not found"} else 400
        return jsonify({"error": error}), status

    max_order = (
        db.session.query(db.func.max(Todo.sort_order))
        .filter_by(
            user_id=current_user.id,
            project_id=todo.project_id,
            status=todo.status,
        )
        .scalar()
        or 0
    )
    todo.sort_order = max_order + 1
    db.session.add(todo)
    db.session.commit()
    return jsonify(serialize_todo(todo)), 201


@api_bp.get("/todos/<int:todo_id>")
@login_required
def get_todo(todo_id):
    todo = get_user_todo(todo_id)
    if not todo:
        return jsonify({"error": "todo not found"}), 404
    return jsonify(serialize_todo(todo))


@api_bp.put("/todos/<int:todo_id>")
@login_required
def update_todo(todo_id):
    todo = get_user_todo(todo_id)
    if not todo:
        return jsonify({"error": "todo not found"}), 404
    payload = request.get_json(silent=True) or {}
    error = apply_todo_payload(todo, payload, partial=True)
    if error:
        status = 404 if error in {"category not found", "project not found"} else 400
        return jsonify({"error": error}), status
    db.session.commit()
    return jsonify(serialize_todo(todo))


@api_bp.delete("/todos/<int:todo_id>")
@login_required
def delete_todo(todo_id):
    todo = get_user_todo(todo_id)
    if not todo:
        return jsonify({"error": "todo not found"}), 404
    shared_root = Path(current_app.config["UPLOAD_FOLDER"]) / "shared_projects"
    for image in list(todo.shared_images):
        (shared_root / f"share_{image.project_share_id}" / image.stored_name).unlink(
            missing_ok=True
        )
    db.session.delete(todo)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/questions")
@login_required
def list_questions():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    category_id = request.args.get("category_id", type=int)
    query = Question.query.filter_by(user_id=current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Question.question.ilike(like), Question.gpt_answer.ilike(like)))
    if status:
        query = query.filter_by(status=status)
    if category_id:
        query = query.filter_by(category_id=category_id)
    questions = query.order_by(Question.updated_at.desc()).all()
    return jsonify([serialize_question(question) for question in questions])


@api_bp.post("/questions")
@login_required
def create_question():
    payload = request.get_json(silent=True) or {}
    question = Question(user_id=current_user.id)
    error = apply_question_payload(question, payload, partial=False)
    if error:
        status = 404 if error == "category not found" else 400
        return jsonify({"error": error}), status
    db.session.add(question)
    db.session.commit()
    return jsonify(serialize_question(question)), 201


@api_bp.get("/questions/<int:question_id>")
@login_required
def get_question(question_id):
    question = get_user_question(question_id)
    if not question:
        return jsonify({"error": "question not found"}), 404
    return jsonify(serialize_question(question))


@api_bp.put("/questions/<int:question_id>")
@login_required
def update_question(question_id):
    question = get_user_question(question_id)
    if not question:
        return jsonify({"error": "question not found"}), 404
    payload = request.get_json(silent=True) or {}
    error = apply_question_payload(question, payload, partial=True)
    if error:
        status = 404 if error == "category not found" else 400
        return jsonify({"error": error}), status
    db.session.commit()
    return jsonify(serialize_question(question))


@api_bp.delete("/questions/<int:question_id>")
@login_required
def delete_question(question_id):
    question = get_user_question(question_id)
    if not question:
        return jsonify({"error": "question not found"}), 404
    image_dir = (
        Path(current_app.config["UPLOAD_FOLDER"])
        / "question_images"
        / f"user_{current_user.id}"
    )
    try:
        for image in list(question.images):
            (image_dir / image.stored_name).unlink(missing_ok=True)
    except PermissionError:
        return jsonify({"error": "question image is in use"}), 409
    db.session.delete(question)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/files")
@login_required
def list_files():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    query = StoredFile.query.filter_by(user_id=current_user.id)
    if q:
        query = query.filter(StoredFile.original_name.ilike(f"%{q}%"))
    if category_id:
        query = query.filter_by(category_id=category_id)
    files = query.order_by(StoredFile.updated_at.desc()).all()
    return jsonify([serialize_file(stored_file) for stored_file in files])


@api_bp.post("/files")
@login_required
def upload_file():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"error": "file is required"}), 400

    upload_dir = user_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    original_name = upload.filename
    safe_name = secure_filename(original_name) or "uploaded_file"
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    target = upload_dir / stored_name
    upload.save(target)

    category_id = request.form.get("category_id", type=int)
    if category_id:
        category = Category.query.filter_by(id=category_id, user_id=current_user.id).first()
        if not category:
            target.unlink(missing_ok=True)
            return jsonify({"error": "category not found"}), 404

    stored_file = StoredFile(
        user_id=current_user.id,
        category_id=category_id or None,
        original_name=original_name,
        stored_name=stored_name,
        content_type=upload.mimetype,
        size_bytes=target.stat().st_size,
    )
    db.session.add(stored_file)
    db.session.commit()
    return jsonify(serialize_file(stored_file)), 201


@api_bp.get("/files/<int:file_id>/download")
@login_required
def download_file(file_id):
    stored_file = get_user_file(file_id)
    if not stored_file:
        return jsonify({"error": "file not found"}), 404
    stored_file.download_count += 1
    db.session.commit()
    return send_from_directory(
        user_upload_dir(),
        stored_file.stored_name,
        as_attachment=True,
        download_name=stored_file.original_name,
    )


@api_bp.delete("/files/<int:file_id>")
@login_required
def delete_file(file_id):
    stored_file = get_user_file(file_id)
    if not stored_file:
        return jsonify({"error": "file not found"}), 404
    path = user_upload_dir() / stored_file.stored_name
    if path.exists():
        path.unlink()
    db.session.delete(stored_file)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/projects")
@login_required
def list_projects():
    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()
    query = Project.query.filter_by(user_id=current_user.id)
    if status:
        query = query.filter_by(status=status)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Project.name.ilike(like), Project.description.ilike(like)))
    projects = query.order_by(Project.updated_at.desc()).all()
    return jsonify([serialize_project(project) for project in projects])


@api_bp.post("/projects")
@login_required
def create_project():
    payload = request.get_json(silent=True) or {}
    project = Project(user_id=current_user.id)
    error = apply_project_payload(project, payload, partial=False)
    if error:
        return jsonify({"error": error}), 400
    db.session.add(project)
    db.session.commit()
    return jsonify(serialize_project(project)), 201


@api_bp.get("/projects/<int:project_id>")
@login_required
def get_project(project_id):
    project = get_user_project(project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404
    return jsonify(serialize_project(project))


@api_bp.put("/projects/<int:project_id>")
@login_required
def update_project(project_id):
    project = get_user_project(project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404
    payload = request.get_json(silent=True) or {}
    error = apply_project_payload(project, payload, partial=True)
    if error:
        return jsonify({"error": error}), 400
    db.session.commit()
    return jsonify(serialize_project(project))


@api_bp.delete("/projects/<int:project_id>")
@login_required
def delete_project(project_id):
    project = get_user_project(project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404
    Todo.query.filter_by(user_id=current_user.id, project_id=project.id).update({"project_id": None})
    db.session.delete(project)
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.put("/todos/<int:todo_id>/status")
@login_required
def update_todo_status(todo_id):
    todo = get_user_todo(todo_id)
    if not todo:
        return jsonify({"error": "todo not found"}), 404
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    if status not in {"Todo", "Doing", "Done", "Cancel"}:
        return jsonify({"error": "invalid status"}), 400
    set_todo_status(todo, status)
    todo.updated_at = utc_now()
    db.session.commit()
    return jsonify(serialize_todo(todo))


@api_bp.put("/todos/reorder")
@login_required
def reorder_todos():
    payload = request.get_json(silent=True) or {}
    items = payload.get("items", [])
    if not isinstance(items, list):
        return jsonify({"error": "items must be a list"}), 400
    valid_statuses = {"Todo", "Doing", "Done", "Cancel"}
    if any(
        not isinstance(item, dict)
        or ("status" in item and item.get("status") not in valid_statuses)
        or not isinstance(item.get("sort_order"), int)
        or item["sort_order"] < 1
        for item in items
    ):
        return jsonify({"error": "invalid reorder item"}), 400

    ids = [item.get("id") for item in items if isinstance(item, dict) and item.get("id")]
    todos = Todo.query.filter(Todo.user_id == current_user.id, Todo.id.in_(ids)).all()
    todo_map = {todo.id: todo for todo in todos}

    for index, item in enumerate(items):
        todo = todo_map.get(item.get("id"))
        if not todo:
            continue
        todo.sort_order = item.get("sort_order", index + 1)
        if item.get("status") and item["status"] != todo.status:
            set_todo_status(todo, item["status"])
        todo.updated_at = utc_now()

    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/search")
@login_required
def global_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"notes": [], "todos": [], "projects": [], "questions": [], "files": []})

    like = f"%{q}%"
    user_id = current_user.id

    notes = (
        Note.query.filter(
            Note.user_id == user_id,
            or_(
                Note.title.ilike(like),
                Note.markdown_content.ilike(like),
                Note.tags.any(Tag.name.ilike(like)),
            ),
        )
        .order_by(Note.updated_at.desc())
        .limit(10)
        .all()
    )
    todos = (
        Todo.query.filter(
            Todo.user_id == user_id,
            or_(Todo.title.ilike(like), Todo.description.ilike(like)),
        )
        .order_by(Todo.updated_at.desc())
        .limit(10)
        .all()
    )
    questions = (
        Question.query.filter(
            Question.user_id == user_id,
            or_(Question.question.ilike(like), Question.gpt_answer.ilike(like)),
        )
        .order_by(Question.updated_at.desc())
        .limit(10)
        .all()
    )
    projects = (
        Project.query.filter(
            Project.user_id == user_id,
            or_(Project.name.ilike(like), Project.description.ilike(like)),
        )
        .order_by(Project.updated_at.desc())
        .limit(10)
        .all()
    )
    files = (
        StoredFile.query.filter(
            StoredFile.user_id == user_id,
            StoredFile.original_name.ilike(like),
        )
        .order_by(StoredFile.updated_at.desc())
        .limit(10)
        .all()
    )

    return jsonify(
        {
            "notes": [
                {"id": n.id, "title": n.title, "url": f"/notes/{n.id}"}
                for n in notes
            ],
            "todos": [
                {"id": t.id, "title": t.title, "status": t.status, "url": f"/todos/{t.id}/edit"}
                for t in todos
            ],
            "questions": [
                {"id": question.id, "question": question.question, "url": f"/questions/{question.id}"}
                for question in questions
            ],
            "projects": [
                {"id": project.id, "name": project.name, "status": project.status, "url": f"/projects/{project.id}"}
                for project in projects
            ],
            "files": [
                {
                    "id": f.id,
                    "name": f.original_name,
                    "url": f"/files/{f.id}/view"
                    if f.original_name.lower().endswith((".md", ".markdown", ".txt"))
                    else f"/files/{f.id}/download",
                }
                for f in files
            ],
        }
    )
