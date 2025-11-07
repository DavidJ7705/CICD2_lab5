import os, time
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

# Pick env file by APP_ENV (default dev)
envfile = {
    "dev": ".env.dev",  #development enviromnet
    "docker": ".env.docker", #docker enviromnet
    "test": ".env.test", #testing enviromnet
}.get(os.getenv("APP_ENV", "dev"), ".env.dev")

# Load environment variables from the selected file
load_dotenv(envfile, override=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db") # default to local sqlite file
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true" # enable sql echo with env varl loggin if its true
RETRIES = int(os.getenv("DB_RETRIES", "10"))
DELAY = float(os.getenv("DB_RETRY_DELAY", "1.5"))

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# small retry (harmless for SQLite, useful for Postgres)
for _ in range(RETRIES):
    try:
        # create the SQLAlchemy engine
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=SQL_ECHO, connect_args=connect_args)
        with engine.connect():  # smoke test connection
            pass
        break
    except OperationalError:
        time.sleep(DELAY)
        
# create a local session
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()