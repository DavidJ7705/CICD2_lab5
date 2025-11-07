from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import engine, SessionLocal
from app.models import Base, UserDB
from app.schemas import UserCreate, UserRead

app = FastAPI()
Base.metadata.create_all(bind=engine)

