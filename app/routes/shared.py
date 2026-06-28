import json
import secrets
import time
import uuid
from datetime import date
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.image_utils import compress_image_to_webp
from app.models import (
    Project,
    ProjectShare,
    ProjectShareAudit,
    SharedTodoImage,
    Todo,
    utc_now,
)


shared_bp = Blueprint("shared", __name__)
VALID_STATUSES = {"Todo", "Doing", "Done", "Cancel"}
STATUS_COLUMNS = [
    ("Todo", "待處理"),
    ("Doing", "進行中"),
    ("Done", "已完成"),
    ("Cancel", "已取消"),
]


def _owner_project(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        abort(404)
    return project


def _available_share(token):
    share = ProjectShare.query.filter_by(token=token).first()
    if not share:
        return None
    if not share.is_active:
        return None
    if share.expires_on and date.today() > share.expires_on:
        return None
    return share


def _share_access(share):
    access = session.get("project_share_access") or {}
    if access.get("share_id") != share.id:
        return None
    nickname = str(access.get("nickname", "")).strip()
    return nickname if nickname else None


def _require_share_access(token):
    share = _available_share(token)
    if not share:
        return None, (jsonify({"error": "share unavailable"}), 410)
    nickname = _share_access(share)
    if not nickname:
        return None, (jsonify({"error": "share access required"}), 401)
    return (share, nickname), None


def _shared_todo(share, todo_id):
    return Todo.query.filter_by(
        id=todo_id,
        user_id=share.project.user_id,
        project_id=share.project_id,
    ).first()


def _set_todo_status(todo, status):
    old_status = todo.status
    todo.status = status
    if status == "Done" and old_status != "Done":
        todo.completed_at = utc_now()
    elif status != "Done":
        todo.completed_at = None


def _audit(share, nickname, action, todo=None, details=None):
    db.session.add(
        ProjectShareAudit(
            project_share_id=share.id,
            todo_id=todo.id if todo else None,
            actor_name=nickname,
            action=action,
            details=json.dumps(details or {}, ensure_ascii=False),
        )
    )


def _serialize_image(image, token):
    return {
        "id": image.id,
        "url": url_for("shared.image_file", token=token, image_id=image.id),
        "width": image.width,
        "height": image.height,
        "size_bytes": image.size_bytes,
        "uploaded_by": image.uploaded_by,
    }


def _serialize_todo(todo, token=None):
    payload = {
        "id": todo.id,
        "title": todo.title,
        "created_by_name": todo.created_by_name,
        "status": todo.status,
        "sort_order": todo.sort_order,
    }
    if token:
        payload["images"] = [_serialize_image(image, token) for image in todo.shared_images]
    return payload


def _share_image_dir(share):
    return (
        Path(current_app.config["UPLOAD_FOLDER"])
        / "shared_projects"
        / f"share_{share.id}"
    )


def _compressed_webp(upload):
    return compress_image_to_webp(
        upload,
        max_source_bytes=current_app.config["SHARED_IMAGE_MAX_SOURCE_BYTES"],
        max_file_bytes=current_app.config["SHARED_IMAGE_MAX_FILE_BYTES"],
    )


@shared_bp.route("/projects/<int:project_id>/share", methods=["GET", "POST"])
@login_required
def manage(project_id):
    project = _owner_project(project_id)
    share = project.share
    error = None

    if request.method == "POST":
        action = request.form.get("action", "save")
        if not share:
            share = ProjectShare(project=project, token=secrets.token_urlsafe(32))
            db.session.add(share)

        if action == "regenerate":
            share.token = secrets.token_urlsafe(32)
            share.is_active = True
            db.session.commit()
            return redirect(url_for("shared.manage", project_id=project.id))

        expires_on = None
        expires_text = request.form.get("expires_on", "").strip()
        if expires_text:
            try:
                expires_on = date.fromisoformat(expires_text)
            except ValueError:
                error = "到期日格式不正確"

        password = request.form.get("password", "")
        if not error:
            share.expires_on = expires_on
            share.is_active = request.form.get("is_active") == "on"
            if request.form.get("remove_password") == "on":
                share.set_password(None)
            elif password:
                share.set_password(password)
            db.session.commit()
            return redirect(url_for("shared.manage", project_id=project.id))

    share_url = (
        url_for("shared.public_board", token=share.token, _external=True)
        if share and share.id
        else None
    )
    audit_logs = (
        ProjectShareAudit.query.filter_by(project_share_id=share.id)
        .order_by(ProjectShareAudit.created_at.desc())
        .limit(50)
        .all()
        if share and share.id
        else []
    )
    return render_template(
        "shared/manage.html",
        title=f"分享 {project.name}",
        active_page="projects",
        project=project,
        share=share,
        share_url=share_url,
        audit_logs=audit_logs,
        error=error,
    )


@shared_bp.route("/shared/<token>", methods=["GET", "POST"])
def public_board(token):
    share = _available_share(token)
    if not share:
        return render_template("shared/unavailable.html", force_public_layout=True), 410

    nickname = _share_access(share)
    error = None
    lock = session.get("project_share_lock") or {}
    locked_until = int(lock.get("until", 0)) if lock.get("share_id") == share.id else 0

    if request.method == "POST" and not nickname:
        if locked_until > int(time.time()):
            error = "密碼錯誤次數過多，請五分鐘後再試"
        else:
            submitted_name = request.form.get("nickname", "").strip()[:80]
            password = request.form.get("password", "")
            password_ok = not share.has_password or share.check_password(password)
            if not submitted_name:
                error = "請輸入暱稱"
            elif not password_ok:
                attempts = int(lock.get("attempts", 0)) + 1
                lock = {"share_id": share.id, "attempts": attempts, "until": 0}
                if attempts >= 5:
                    lock["until"] = int(time.time()) + 300
                    lock["attempts"] = 0
                session["project_share_lock"] = lock
                error = "分享密碼錯誤"
            else:
                session["project_share_access"] = {
                    "share_id": share.id,
                    "nickname": submitted_name,
                }
                session.pop("project_share_lock", None)
                return redirect(url_for("shared.public_board", token=token))

    if not nickname:
        return render_template(
            "shared/access.html",
            project=share.project,
            share=share,
            error=error,
            locked=locked_until > int(time.time()),
            force_public_layout=True,
        )

    todos = (
        Todo.query.filter_by(
            user_id=share.project.user_id,
            project_id=share.project_id,
        )
        .order_by(Todo.status.asc(), Todo.sort_order.asc(), Todo.created_at.desc())
        .all()
    )
    groups = [
        {
            "status": status,
            "title": title,
            "todos": [todo for todo in todos if todo.status == status],
        }
        for status, title in STATUS_COLUMNS
    ]
    return render_template(
        "shared/board.html",
        project=share.project,
        share=share,
        nickname=nickname,
        groups=groups,
        force_public_layout=True,
    )


@shared_bp.post("/shared/<token>/leave")
def leave(token):
    share = ProjectShare.query.filter_by(token=token).first()
    access = session.get("project_share_access") or {}
    if share and access.get("share_id") == share.id:
        session.pop("project_share_access", None)
    return redirect(url_for("shared.public_board", token=token))


@shared_bp.post("/shared/<token>/api/todos")
def create_todo(token):
    access, error = _require_share_access(token)
    if error:
        return error
    share, nickname = access
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()[:500]
    status = payload.get("status", "Todo")
    if not title:
        return jsonify({"error": "title is required"}), 400
    if status not in VALID_STATUSES:
        return jsonify({"error": "invalid status"}), 400
    max_order = (
        db.session.query(db.func.max(Todo.sort_order))
        .filter_by(
            user_id=share.project.user_id,
            project_id=share.project_id,
            status=status,
        )
        .scalar()
        or 0
    )
    todo = Todo(
        user_id=share.project.user_id,
        project_id=share.project_id,
        title=title,
        created_by_name=nickname,
        status=status,
        sort_order=max_order + 1,
    )
    if status == "Done":
        todo.completed_at = utc_now()
    db.session.add(todo)
    db.session.flush()
    _audit(share, nickname, "create", todo, {"title": title, "status": status})
    db.session.commit()
    return jsonify(_serialize_todo(todo, token)), 201


@shared_bp.put("/shared/<token>/api/todos/<int:todo_id>")
def edit_todo(token, todo_id):
    access, error = _require_share_access(token)
    if error:
        return error
    share, nickname = access
    todo = _shared_todo(share, todo_id)
    if not todo:
        return jsonify({"error": "todo not found"}), 404
    payload = request.get_json(silent=True) or {}
    title = str(payload.get("title", "")).strip()[:500]
    if not title:
        return jsonify({"error": "title is required"}), 400
    before = {"title": todo.title}
    todo.title = title
    todo.updated_at = utc_now()
    _audit(
        share,
        nickname,
        "edit",
        todo,
        {
            "before": before,
            "after": {"title": todo.title},
        },
    )
    db.session.commit()
    return jsonify(_serialize_todo(todo, token))


@shared_bp.put("/shared/<token>/api/todos/<int:todo_id>/status")
def update_status(token, todo_id):
    access, error = _require_share_access(token)
    if error:
        return error
    share, nickname = access
    todo = _shared_todo(share, todo_id)
    if not todo:
        return jsonify({"error": "todo not found"}), 404
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    if status not in VALID_STATUSES:
        return jsonify({"error": "invalid status"}), 400
    old_status = todo.status
    _set_todo_status(todo, status)
    todo.updated_at = utc_now()
    _audit(share, nickname, "status", todo, {"from": old_status, "to": status})
    db.session.commit()
    return jsonify(_serialize_todo(todo, token))


@shared_bp.post("/shared/<token>/api/todos/<int:todo_id>/images")
def upload_image(token, todo_id):
    access, error = _require_share_access(token)
    if error:
        return error
    share, nickname = access
    todo = _shared_todo(share, todo_id)
    if not todo:
        return jsonify({"error": "todo not found"}), 404
    if len(todo.shared_images) >= current_app.config["SHARED_IMAGE_MAX_PER_TODO"]:
        return jsonify({"error": "每個待辦最多 3 張圖片"}), 400

    used_bytes = (
        db.session.query(db.func.sum(SharedTodoImage.size_bytes))
        .filter_by(project_share_id=share.id)
        .scalar()
        or 0
    )
    upload = request.files.get("image")
    if not upload or not upload.filename:
        return jsonify({"error": "請選擇圖片"}), 400
    try:
        image_bytes, width, height = _compressed_webp(upload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if used_bytes + len(image_bytes) > current_app.config["SHARED_IMAGE_PROJECT_QUOTA_BYTES"]:
        return jsonify({"error": "此分享專案的圖片容量已達 30MB"}), 400

    stored_name = f"{uuid.uuid4().hex}.webp"
    image_dir = _share_image_dir(share)
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / stored_name
    image_path.write_bytes(image_bytes)
    image = SharedTodoImage(
        todo_id=todo.id,
        project_share_id=share.id,
        stored_name=stored_name,
        size_bytes=len(image_bytes),
        width=width,
        height=height,
        uploaded_by=nickname,
    )
    db.session.add(image)
    db.session.flush()
    _audit(
        share,
        nickname,
        "image_upload",
        todo,
        {"image_id": image.id, "size_bytes": image.size_bytes},
    )
    try:
        db.session.commit()
    except Exception:
        image_path.unlink(missing_ok=True)
        raise
    return jsonify(_serialize_image(image, token)), 201


@shared_bp.get("/shared/<token>/images/<int:image_id>")
def image_file(token, image_id):
    access, error = _require_share_access(token)
    if error:
        return error
    share, _nickname = access
    image = SharedTodoImage.query.filter_by(
        id=image_id,
        project_share_id=share.id,
    ).first()
    if not image:
        abort(404)
    return send_from_directory(
        _share_image_dir(share),
        image.stored_name,
        mimetype="image/webp",
        max_age=86400,
    )


@shared_bp.delete("/shared/<token>/api/images/<int:image_id>")
def delete_image(token, image_id):
    access, error = _require_share_access(token)
    if error:
        return error
    share, nickname = access
    image = SharedTodoImage.query.filter_by(
        id=image_id,
        project_share_id=share.id,
    ).first()
    if not image:
        return jsonify({"error": "image not found"}), 404
    todo = _shared_todo(share, image.todo_id)
    if not todo:
        return jsonify({"error": "todo not found"}), 404
    image_path = _share_image_dir(share) / image.stored_name
    _audit(
        share,
        nickname,
        "image_remove",
        todo,
        {"image_id": image.id, "uploaded_by": image.uploaded_by},
    )
    try:
        image_path.unlink(missing_ok=True)
    except PermissionError:
        db.session.rollback()
        return jsonify({"error": "圖片正在使用中，請稍後再試"}), 409
    db.session.delete(image)
    db.session.commit()
    return jsonify({"ok": True})


@shared_bp.put("/shared/<token>/api/todos/reorder")
def reorder(token):
    access, error = _require_share_access(token)
    if error:
        return error
    share, nickname = access
    payload = request.get_json(silent=True) or {}
    items = payload.get("items", [])
    if not isinstance(items, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("id"), int)
        or item.get("status") not in VALID_STATUSES
        or not isinstance(item.get("sort_order"), int)
        or item["sort_order"] < 1
        for item in items
    ):
        return jsonify({"error": "invalid reorder items"}), 400

    ids = [item["id"] for item in items]
    if len(ids) != len(set(ids)):
        return jsonify({"error": "duplicate todo ids"}), 400
    todos = Todo.query.filter(
        Todo.user_id == share.project.user_id,
        Todo.project_id == share.project_id,
        Todo.id.in_(ids),
    ).all()
    todo_map = {todo.id: todo for todo in todos}
    if len(todo_map) != len(set(ids)):
        return jsonify({"error": "todo not found"}), 404

    status_changes = []
    for item in items:
        todo = todo_map[item["id"]]
        if todo.status != item["status"]:
            status_changes.append(
                {"todo_id": todo.id, "from": todo.status, "to": item["status"]}
            )
            _set_todo_status(todo, item["status"])
        todo.sort_order = item["sort_order"]
        todo.updated_at = utc_now()
    _audit(
        share,
        nickname,
        "reorder",
        details={"items": len(items), "status_changes": status_changes},
    )
    db.session.commit()
    return jsonify({"ok": True})
