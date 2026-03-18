import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum

DATABASE_URL = "sqlite:///./drama_pipeline.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProjectStatus(str, enum.Enum):
    CREATED = "created"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"


class StageStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    total_episodes = Column(Integer, default=0)
    batch_size = Column(Integer, default=50)
    target_language = Column(String, default="en")
    status = Column(String, default=ProjectStatus.CREATED)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    config = Column(JSON, default=dict)
    batches = relationship("Batch", back_populates="project", cascade="all, delete-orphan")


class Batch(Base):
    __tablename__ = "batches"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    batch_number = Column(Integer, nullable=False)
    start_episode = Column(Integer, nullable=False)
    end_episode = Column(Integer, nullable=False)
    status = Column(String, default=ProjectStatus.CREATED)
    progress = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    project = relationship("Project", back_populates="batches")
    episodes = relationship("Episode", back_populates="batch", cascade="all, delete-orphan")


class Episode(Base):
    __tablename__ = "episodes"
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    episode_number = Column(Integer, nullable=False)
    title = Column(String, default="")
    duration_seconds = Column(Integer, default=0)
    status = Column(String, default=StageStatus.PENDING)
    current_stage = Column(String, default="")
    # File references
    source_type = Column(String, default="")  # "srt", "video", ""
    source_file = Column(String, default="")  # path to uploaded file
    raw_subtitles = Column(JSON, nullable=True)  # parsed subtitle lines from SRT/ASR
    s1_status = Column(String, default=StageStatus.PENDING)
    s2_status = Column(String, default=StageStatus.PENDING)
    s3_status = Column(String, default=StageStatus.PENDING)
    s5_status = Column(String, default=StageStatus.PENDING)
    s6_status = Column(String, default=StageStatus.PENDING)
    s7_status = Column(String, default=StageStatus.PENDING)
    qa_status = Column(String, default=StageStatus.PENDING)
    # Results stored as JSON
    subtitle_data = Column(JSON, nullable=True)
    characters = Column(JSON, nullable=True)
    emotions = Column(JSON, nullable=True)
    script = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    emotion_analysis = Column(JSON, nullable=True)
    hooks = Column(JSON, nullable=True)
    qa_result = Column(JSON, nullable=True)
    batch = relationship("Batch", back_populates="episodes")


class CharacterDB(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    aliases = Column(JSON, default=list)
    description = Column(Text, default="")
    first_appearance = Column(Integer, default=1)
    relationships = Column(JSON, default=dict)


class PipelineLog(Base):
    __tablename__ = "pipeline_logs"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    batch_id = Column(Integer, nullable=True)
    episode_id = Column(Integer, nullable=True)
    stage = Column(String, nullable=False)
    level = Column(String, default="info")
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(JSON, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
