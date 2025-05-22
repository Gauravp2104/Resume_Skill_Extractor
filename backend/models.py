from sqlalchemy import Column, String, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    filename = Column(String)
    file_path = Column(String)
    created_at = Column(DateTime)
    resume_data = Column(JSON)

class ResumeAnalysis(Base):
    __tablename__ = 'resume_analyses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(String)
    analysis_data = Column(JSON)
    tags = Column(JSON)
    created_at = Column(DateTime)
    processed_at = Column(DateTime)    
