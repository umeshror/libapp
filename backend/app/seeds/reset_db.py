from app.db.session import engine
from sqlalchemy import text


def reset_db():
    print("Dropping and recreating public schema...")
    try:
        with engine.connect() as conn:
            # Postgres specific schema reset
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            conn.commit()
        print("Database reset successful.")
    except Exception as e:
        print(f"Error resetting database: {e}")


if __name__ == "__main__":
    reset_db()
