# app/schemas.py
from typing import Annotated, Optional, List
from annotated_types import Ge, Le
from pydantic import BaseModel, EmailStr, ConfigDict, StringConstraints, Field

NameStr = Annotated[str, StringConstraints(min_length=2, max_length=50)]
StudentId = Annotated[str, StringConstraints(pattern=r"^S\d{7}$")]
CodeStr = Annotated[str, StringConstraints(min_length=1, max_length=32)]
CourseNameStr = Annotated[str, StringConstraints(min_length=1, max_length=255)]
ProjectNameStr = Annotated[str, StringConstraints(min_length=1, max_length=255)]
DescStr = Annotated[str, StringConstraints(min_length=0, max_length=2000)]

AgeInt = Annotated[int, Ge(0), Le(150)]
CreditsInt = Annotated[int, Ge(1), Le(120)]

class UserCreate(BaseModel):
    name: NameStr
    email: EmailStr
    age: int = Field(gt=18)
    student_id: StudentId

class UserRead(BaseModel):
    id: int
    name: NameStr
    email: EmailStr
    age: int
    student_id: StudentId
    model_config = ConfigDict(from_attributes=True)

class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: ProjectNameStr
    description: Optional[DescStr] = None
    owner_id: int

class UserReadWithProjects(UserRead):
    projects: List[ProjectRead] = []

# ---------- Projects ----------
# Flat route: POST /api/projects (owner_id in body)
class ProjectCreate(BaseModel):
    name: ProjectNameStr
    description: Optional[DescStr] = None
    owner_id: int

# Nested route: POST /api/users/{user_id}/projects (owner implied by path)
class ProjectCreateForUser(BaseModel):
    name: ProjectNameStr
    description: Optional[DescStr] = None
class ProjectReadWithOwner(ProjectRead):
    owner: Optional["UserRead"] = None # use selectinload(ProjectDB.owner) when querying

# ---------- Courses ----------
class CourseCreate(BaseModel):
    code: CodeStr
    name: CourseNameStr
    credits: CreditsInt
    
class CourseRead(CourseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int