from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.db.base import Base

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Import all models before create_all
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Idempotent SQLite migrations for existing databases
    if settings.DATABASE_URL.startswith("sqlite"):
        from sqlalchemy import text
        with engine.connect() as conn:
            # Check agents table
            try:
                res = conn.execute(text("PRAGMA table_info(agents)")).fetchall()
                cols = {row[1] for row in res}
                if "adapter_type" not in cols:
                    conn.execute(text("ALTER TABLE agents ADD COLUMN adapter_type VARCHAR(32) DEFAULT 'python'"))
                if "registration_source" not in cols:
                    conn.execute(text("ALTER TABLE agents ADD COLUMN registration_source VARCHAR(32) DEFAULT 'built_in'"))
                if "declared_capabilities_json" not in cols:
                    conn.execute(text("ALTER TABLE agents ADD COLUMN declared_capabilities_json TEXT DEFAULT '[]'"))
                if "adapter_config_json" not in cols:
                    conn.execute(text("ALTER TABLE agents ADD COLUMN adapter_config_json TEXT DEFAULT '{}'"))
                if "observability_level" not in cols:
                    conn.execute(text("ALTER TABLE agents ADD COLUMN observability_level VARCHAR(32) DEFAULT 'level_3_instrumented_tools'"))
                conn.commit()
            except Exception:
                pass

            # Check scenarios table
            try:
                res = conn.execute(text("PRAGMA table_info(scenarios)")).fetchall()
                cols = {row[1] for row in res}
                if "required_capabilities_json" not in cols:
                    conn.execute(text("ALTER TABLE scenarios ADD COLUMN required_capabilities_json TEXT DEFAULT '[]'"))
                conn.commit()
            except Exception:
                pass

            # Check test_runs table
            try:
                res = conn.execute(text("PRAGMA table_info(test_runs)")).fetchall()
                cols = {row[1] for row in res}
                if "unsupported_scenarios" not in cols:
                    conn.execute(text("ALTER TABLE test_runs ADD COLUMN unsupported_scenarios INTEGER DEFAULT 0"))
                if "observability_level" not in cols:
                    conn.execute(text("ALTER TABLE test_runs ADD COLUMN observability_level VARCHAR(32) DEFAULT 'level_3_instrumented_tools'"))
                conn.commit()
            except Exception:
                pass
