from app.core.config import settings
from sqlalchemy import create_engine, text

def reset_test_db():
    # Connect to 'postgres' DB to drop/create 'library_test'
    # Use same credentials as configured in settings
    base_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    engine = create_engine(base_url)
    test_db = "library_test"
    
    print(f"DEBUG: Resetting database {test_db}")
    
    with engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        
        # Kill all connections to the test DB
        print(f"DEBUG: Killing connections to {test_db}")
        kill_query = text(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{test_db}'
              AND pid <> pg_backend_pid();
        """)
        try:
            conn.execute(kill_query)
        except Exception as e:
            print(f"DEBUG: Error killing connections: {e}")
        
        # Drop and recreate
        print(f"DEBUG: Dropping {test_db}")
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_db}"))
        print(f"DEBUG: Creating {test_db}")
        conn.execute(text(f"CREATE DATABASE {test_db}"))

if __name__ == "__main__":
    reset_test_db()
