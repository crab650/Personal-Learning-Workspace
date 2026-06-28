from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


def utc_now():
    return datetime.now(timezone.utc)


note_tags = db.Table(
    "note_tags",
    db.Column("note_id", db.Integer, db.ForeignKey("notes.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active_flag = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.is_active_flag


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    color = db.Column(db.String(20), default="#3b82f6", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    user = db.relationship("User", backref="categories")

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_category_user_name"),)


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    user = db.relationship("User", backref="tags")

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_tag_user_name"),)


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    markdown_content = db.Column(db.Text, default="", nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = db.relationship("User", backref="notes")
    category = db.relationship("Category", backref="notes")
    tags = db.relationship("Tag", secondary=note_tags, backref="notes")
    images = db.relationship(
        "NoteImage",
        back_populates="note",
        cascade="all, delete-orphan",
        order_by="NoteImage.created_at.asc()",
    )


class NoteImage(db.Model):
    __tablename__ = "note_images"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    note_id = db.Column(
        db.Integer,
        db.ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    upload_session = db.Column(db.String(64), nullable=True, index=True)
    stored_name = db.Column(db.String(80), nullable=False, unique=True)
    size_bytes = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    note = db.relationship("Note", back_populates="images")
    user = db.relationship("User", backref="note_images")


class Todo(db.Model):
    __tablename__ = "todos"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    title = db.Column(db.String(500), nullable=False)
    created_by_name = db.Column(db.String(80), nullable=True)
    description = db.Column(db.Text, default="", nullable=False)
    priority = db.Column(db.String(20), default="Medium", nullable=False)
    status = db.Column(db.String(20), default="Todo", nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    reminder_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = db.relationship("User", backref="todos")
    category = db.relationship("Category", backref="todos")
    project = db.relationship("Project", backref="todos")
    shared_images = db.relationship(
        "SharedTodoImage",
        back_populates="todo",
        cascade="all, delete-orphan",
    )


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default="", nullable=False)
    status = db.Column(db.String(20), default="Active", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = db.relationship("User", backref="projects")
    share = db.relationship(
        "ProjectShare",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_project_user_name"),)


class ProjectShare(db.Model):
    __tablename__ = "project_shares"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    token = db.Column(db.String(96), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    expires_on = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    project = db.relationship("Project", back_populates="share")
    audit_logs = db.relationship(
        "ProjectShareAudit",
        back_populates="share",
        cascade="all, delete-orphan",
        order_by="ProjectShareAudit.created_at.desc()",
    )
    images = db.relationship(
        "SharedTodoImage",
        back_populates="share",
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password) if password else None

    def check_password(self, password):
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)

    @property
    def has_password(self):
        return bool(self.password_hash)


class ProjectShareAudit(db.Model):
    __tablename__ = "project_share_audits"

    id = db.Column(db.Integer, primary_key=True)
    project_share_id = db.Column(
        db.Integer,
        db.ForeignKey("project_shares.id"),
        nullable=False,
        index=True,
    )
    todo_id = db.Column(
        db.Integer,
        db.ForeignKey("todos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_name = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(30), nullable=False)
    details = db.Column(db.Text, default="", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    share = db.relationship("ProjectShare", back_populates="audit_logs")


class SharedTodoImage(db.Model):
    __tablename__ = "shared_todo_images"

    id = db.Column(db.Integer, primary_key=True)
    todo_id = db.Column(
        db.Integer,
        db.ForeignKey("todos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_share_id = db.Column(
        db.Integer,
        db.ForeignKey("project_shares.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stored_name = db.Column(db.String(80), nullable=False, unique=True)
    size_bytes = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    uploaded_by = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    todo = db.relationship("Todo", back_populates="shared_images")
    share = db.relationship("ProjectShare", back_populates="images")


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    question = db.Column(db.Text, nullable=False)
    gpt_answer = db.Column(db.Text, default="", nullable=False)
    is_understood = db.Column(db.Boolean, default=False, nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(20), default="Open", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = db.relationship("User", backref="questions")
    category = db.relationship("Category", backref="questions")
    images = db.relationship(
        "QuestionImage",
        back_populates="question_item",
        cascade="all, delete-orphan",
        order_by="QuestionImage.created_at.asc()",
    )


class QuestionImage(db.Model):
    __tablename__ = "question_images"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    upload_session = db.Column(db.String(64), nullable=True, index=True)
    stored_name = db.Column(db.String(80), nullable=False, unique=True)
    size_bytes = db.Column(db.Integer, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)

    question_item = db.relationship("Question", back_populates="images")
    user = db.relationship("User", backref="question_images")


class StoredFile(db.Model):
    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(120), nullable=True)
    size_bytes = db.Column(db.Integer, default=0, nullable=False)
    download_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = db.relationship("User", backref="files")
    category = db.relationship("Category", backref="files")


class ApiLog(db.Model):
    __tablename__ = "api_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    method = db.Column(db.String(10), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    key = db.Column(db.String(120), nullable=False)
    value = db.Column(db.Text, default="", nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user = db.relationship("User", backref="settings")

    __table_args__ = (db.UniqueConstraint("user_id", "key", name="uq_setting_user_key"),)
