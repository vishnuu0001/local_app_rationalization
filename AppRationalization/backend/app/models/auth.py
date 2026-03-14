from datetime import datetime

from app import db

APP_RATIONALIZATION = "APP_RATIONALIZATION"
CODE_ANALYSIS = "CODE_ANALYSIS"
SUPPORTED_APPS = {APP_RATIONALIZATION, CODE_ANALYSIS}


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.UniqueConstraint("oauth_provider", "oauth_subject", name="uq_oauth_identity"),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(32), nullable=False, default="user")
    oauth_provider = db.Column(db.String(32), nullable=True)
    oauth_subject = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    permissions = db.relationship(
        "UserAppPermission",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )
    sessions = db.relationship(
        "UserSession",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        apps = sorted({perm.app_key for perm in self.permissions})
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "apps": apps,
            "oauth_provider": self.oauth_provider,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserAppPermission(db.Model):
    __tablename__ = "user_app_permissions"
    __table_args__ = (
        db.UniqueConstraint("user_id", "app_key", name="uq_user_app_permission"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    app_key = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "app_key": self.app_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserSession(db.Model):
    __tablename__ = "user_sessions"
    __table_args__ = (
        db.UniqueConstraint("session_id", name="uq_user_session_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(128), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @property
    def is_active(self):
        return self.revoked_at is None and self.expires_at >= datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
        }
