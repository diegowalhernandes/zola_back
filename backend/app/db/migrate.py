from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _column_names(inspector, table: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table)}


def run_migrations(engine: Engine) -> None:
    inspector = inspect(engine)

    if "professionals" in inspector.get_table_names():
        columns = _column_names(inspector, "professionals")
        with engine.begin() as conn:
            if "professional_type" not in columns:
                conn.execute(text("ALTER TABLE professionals ADD COLUMN professional_type VARCHAR(20)"))
            if "job_specs" not in columns:
                conn.execute(text("ALTER TABLE professionals ADD COLUMN job_specs TEXT"))
            if "availability" not in columns:
                conn.execute(text("ALTER TABLE professionals ADD COLUMN availability TEXT"))

    if "appointments" not in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        professional_id INTEGER NOT NULL,
                        client_id INTEGER NOT NULL,
                        appointment_date DATE NOT NULL,
                        time_slot VARCHAR(10) NOT NULL,
                        status VARCHAR(30) DEFAULT 'pending',
                        notes TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(professional_id) REFERENCES professionals(id),
                        FOREIGN KEY(client_id) REFERENCES users(id)
                    )
                    """
                )
            )
