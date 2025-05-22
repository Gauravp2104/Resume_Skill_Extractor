from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid

class Metadata(BaseModel):
    name: str
    email: str
    phone: str

class Experience(BaseModel):
    role: str
    company: str
    duration: str
    location: str
    description: str

class Education(BaseModel):
    degree: str
    institution: str
    year: str

class Project(BaseModel):
    name: str
    description: str
    technologies: str

class ResumeBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "default_user"
    filename: str

class ResumeCreate(ResumeBase):
    minio_object_name: str
    content: bytes  # Only used during upload

class ResumeResponse(ResumeBase):
    created_at: datetime
    resume_data: Optional[dict] = None
    download_url: Optional[str] = None  
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            bytes: lambda v: v.decode('latin-1') if v else None
        }

class ResumeAnalysisResponse(BaseModel):
    metadata: Metadata
    skills: List[str]
    experience: List[Experience]
    education: List[Education]
    projects: List[Project]
    processed_at: datetime 
