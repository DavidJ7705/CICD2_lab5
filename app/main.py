from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import Base
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from .database import engine, SessionLocal
from .models import Base, UserDB, CourseDB, ProjectDB
from .schemas import (
    UserCreate, UserRead,
    CourseCreate, CourseRead,
    ProjectCreate, ProjectRead,
    ProjectReadWithOwner, ProjectCreateForUser
)

#Replacing @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)   
    yield

app = FastAPI(lifespan=lifespan)

# CORS (add this block)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev-friendly; tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status": "ok"}

def commit_or_rollback(db: Session, error_msg: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=error_msg)

    
@app.post("/api/courses", response_model=CourseRead, status_code=201, summary="You could add details")
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    """
    Create a new course entry,
    fails if a course exists already with the same unique fields
    """
    db_course = CourseDB(**course.model_dump())
    db.add(db_course)
    commit_or_rollback(db, "Course already exists")
    db.refresh(db_course)
    return db_course

@app.get("/api/courses", response_model=list[CourseRead])
def list_courses(limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    """
    Get a list of all courses,
    """
    stmt = select(CourseDB).order_by(CourseDB.id).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()

# -------------- Projects --------------
@app.post("/api/projects", response_model=ProjectRead, status_code=201)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new project for a given user,
    ensures the user exists before creating a project
    """
    user = db.get(UserDB, project.owner_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    proj = ProjectDB(
        name=project.name,
        description=project.description,
        owner_id=project.owner_id,
    )
    db.add(proj)
    commit_or_rollback(db, "Project creation failed")
    db.refresh(proj)
    return proj

@app.get("/api/projects", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    stmt = select(ProjectDB).order_by(ProjectDB.id)
    return db.execute(stmt).scalars().all()

@app.get("/api/projects/{project_id}", response_model=ProjectReadWithOwner)
def get_project_with_owner(project_id: int, db: Session = Depends(get_db)):
    """
    Get a single project by id and return its details with the owners,
    selectionload loads the owner relationship
    """
    stmt = select(ProjectDB).where(ProjectDB.id == project_id).options(selectinload(ProjectDB.owner))
    proj = db.execute(stmt).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

@app.put("/api/projects/{project_id}", response_model=ProjectRead, status_code=status.HTTP_200_OK)
def update_project(project_id: int, project: ProjectCreate, db: Session = Depends(get_db)):
    """
    Fully update a projects fields,
    requires all fields(not partial)
    """
    proj = db.get(ProjectDB, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    owner = db.get(UserDB, project.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner user not found")


    for field, value in project.model_dump().items():
        setattr(proj, field, value)

    commit_or_rollback(db, "Project update failed")
    db.refresh(proj)
    return proj

@app.patch("/api/projects/{project_id}", response_model=ProjectRead, status_code=status.HTTP_200_OK)
def patch_project(project_id: int, partial_project: dict, db: Session = Depends(get_db)):
    """
    Partially update a projects fields
    """
    proj = db.get(ProjectDB, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if "owner_id" in partial_project: # if the owner exists in the object
        owner = db.get(UserDB, partial_project["owner_id"])
        if not owner:
            raise HTTPException(status_code=404, detail="Owner user not found")

    #update each field that is in the json request
    for field, value in partial_project.items():
        if hasattr(proj, field):
            setattr(proj, field, value)

    commit_or_rollback(db, "Project partial update failed")
    db.refresh(proj)
    return proj


# -------------- USERS --------------

#Nested Routes
@app.get("/api/users/{user_id}/projects", response_model=list[ProjectRead])
def get_user_projects(user_id: int, db: Session = Depends(get_db)):
    stmt = select(ProjectDB).where(ProjectDB.owner_id == user_id)
    #space it out for debugging
    result = db.execute(stmt)
    rows = result.scalars().all()
    return rows
    #return db.execute(stmt).scalars().all()

@app.post("/api/users/{user_id}/projects", response_model=ProjectRead, status_code=201)
def create_user_project(user_id: int, project: ProjectCreateForUser, db: Session = Depends(get_db)):
    user = db.get(UserDB, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    proj = ProjectDB(
        name=project.name,
        description=project.description, # <-- set it
        owner_id=user_id
    )
    db.add(proj)
    commit_or_rollback(db, "Project creation failed")
    db.refresh(proj)
    return proj



@app.get("/api/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    stmt = select(UserDB).order_by(UserDB.id)
    #Useful for debugging
    result = db.execute(stmt)
    users = result.scalars().all()
    return users
    #return list(db.execute(stmt).scalars())


@app.get("/api/users/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(UserDB, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def add_user(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user,
    automatically commits and refreshes the object 
    """
    user = UserDB(**payload.model_dump())
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists")
    return user

# DELETE a user (triggers ORM cascade -> deletes their projects too)
@app.delete("/api/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> Response:
    user = db.get(UserDB, user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user) # <-- triggers cascade="all, delete-orphan" on projects
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.put("/api/users/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
def update_user(user_id: int, updated_user: UserCreate, db: Session = Depends(get_db)) -> Response:
    """
    Fully update a user's record.
    PUT expects the full payload (name, email, student_id).
    """
    result = (db.query(UserDB).filter(UserDB.id == user_id).update(updated_user.model_dump())) #attempt to update user with provided fields
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    commit_or_rollback(db, "User update failed (duplicate email or student_id)")

    user = db.get(UserDB, user_id)
    return user

@app.patch("/api/users/{user_id}", response_model=UserRead, status_code=status.HTTP_200_OK)
def patch_user(user_id: int, partial_user: dict, db: Session = Depends(get_db)):
    """
    Partially update a user's record (PATCH = partial fields).
    For example: {"email": "new@example.com"}.
    """
    result = (db.query(UserDB).filter(UserDB.id == user_id).update(partial_user))  #attempt to update user with provided fields

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    commit_or_rollback(db, "User partial update failed")
    user = db.get(UserDB, user_id)
    return user