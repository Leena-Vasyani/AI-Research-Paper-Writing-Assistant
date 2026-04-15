from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import uuid
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "sqlite:///./data/sessions.db"
)

Base = declarative_base()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine)


class ChatSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ChatMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


Base.metadata.create_all(engine)


def _migrate_sqlite_schema():
    """Apply lightweight migrations for existing local SQLite databases."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "sessions" not in inspector.get_table_names():
        return

    session_columns = {
        column["name"]
        for column in inspector.get_columns("sessions")
    }

    if "last_active" not in session_columns:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE sessions "
                    "ADD COLUMN last_active DATETIME"
                )
            )
            conn.execute(
                text(
                    "UPDATE sessions "
                    "SET last_active = created_at "
                    "WHERE last_active IS NULL"
                )
            )


_migrate_sqlite_schema()


def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(engine)
    _migrate_sqlite_schema()


def create_session(name: str | None = None):
    db = SessionLocal()

    count = db.query(ChatSession).count()
    if name is None:
        name = f"Chat {count + 1}"

    session_id = str(uuid.uuid4())
    session = ChatSession(
        id=session_id,
        name=name,
    )

    db.add(session)
    db.commit()
    db.close()
    return session_id


def save_message(session_id, role, content):
    db = SessionLocal()
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
    )
    db.add(msg)
    db.commit()
    db.close()


def load_messages(session_id):
    db = SessionLocal()
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    db.close()

    return [
        {"role": m.role, "content": m.content}
        for m in msgs
    ]


def list_sessions():
    db = SessionLocal()
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    db.close()

    return [
        {
            "id": s.id,
            "name": s.name,
            "created_at": s.created_at,
        }
        for s in sessions
    ]
