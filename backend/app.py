from math import log
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import Base, Resume, ResumeAnalysis
from schemas import ResumeCreate, ResumeResponse, ResumeAnalysisResponse
from database import SessionLocal, engine, get_db
import logging
import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from io import BytesIO
import PyPDF2
import re
from analysis_utils import (
    GLOBAL_SKILLS,
    RESUME_SKILL_MAPPING,
    _finalize_project,
    clean_name,
    normalize_skills,
    track_skills,
    get_filtered_skills,
    extract_resume_entities,
    nlp_bert,
    nlp_spacy,
    extract_text_from_pdf,
    extract_experience_details,
    extract_education_details,
    extract_skills,
    store_analysis_result,
    extract_projects,
    get_best_name_candidate,
    clean_skills
)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Resume API",
    version="1.0.0",
    description="API for uploading, managing, and analyzing PDF resumes using BERT NER"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
Base.metadata.create_all(bind=engine)

# # Initialize BERT NER pipeline
# try:
#     tokenizer = AutoTokenizer.from_pretrained("dslim/bert-base-NER")
#     model = AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")
#     DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
#     model.to(DEVICE)
#     nlp = pipeline(
#         "ner",
#         model=model,
#         tokenizer=tokenizer,
#         aggregation_strategy="simple",
#         device=0 if DEVICE == "cuda" else -1
#     )
#     logger.info("BERT NER model loaded successfully")
# except Exception as e:
#     logger.error(f"Failed to load BERT NER model: {str(e)}")
#     raise RuntimeError("Failed to initialize NER model")

@app.on_event("startup")
def startup_event():
    """Initialize services on startup"""
    logger.info("Starting up application")

@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down application")

UPLOAD_DIR = "resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """Upload a PDF resume to local storage"""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, detail="Only PDF files allowed")

    existing_resume = db.query(Resume).filter(
        Resume.user_id == user_id,
        Resume.filename == file.filename
    ).first()

    if existing_resume:
        raise HTTPException(409, detail="A resume with this filename already exists")

    file_id = str(uuid.uuid4())
    local_file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    
    try:
        contents = await file.read()
        
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(413, detail="File too large (max 10MB)")

        with open(local_file_path, "wb") as f:
            f.write(contents)
        
        db_resume = Resume(
            id=file_id,
            user_id=user_id,
            filename=file.filename,
            file_path=local_file_path,
            created_at=datetime.utcnow(),
            resume_data={
                "size": len(contents),
                "content_type": file.content_type,
                "original_filename": file.filename
            }
        )
        
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)
        
        return ResumeResponse(
            **db_resume.__dict__,
            download_url=f"/resumes/{file_id}/download"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(500, detail="File upload failed")   


@app.get("/resumes", response_model=List[ResumeResponse])
def list_resumes(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """List all resumes for a user"""
    try:
        resumes = db.query(Resume).filter(Resume.user_id == user_id).all()
        
        response = []
        for resume in resumes:
            response.append(ResumeResponse(
                **resume.__dict__,
                download_url=f"/resumes/{resume.id}/download"
            ))
                
        return response
    except Exception as e:
        logger.error(f"List resumes failed: {str(e)}", exc_info=True)
        raise HTTPException(500, detail="Failed to retrieve resumes")

@app.get("/resumes/search", response_model=List[ResumeResponse], status_code=200)
async def enhanced_search(
    query: str = Query(..., min_length=2),  # Expects ?query=param
    db: Session = Depends(get_db)
):   
    try:
        results = db.query(Resume).filter(
            Resume.filename.ilike(f"%{query}%")  # Simplified to just filename search
        ).all()
        
        if not results:
            return []
            
        return [ResumeResponse(
            **resume.__dict__,
            download_url=f"/resumes/{resume.id}/download"
        ) for resume in results]
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(500, detail="Search service unavailable")

@app.get("/resumes/filter")
def filter_resumes(
    skills: List[str] = Query([])
):
    if not skills:
        return []
    
    # Convert skills to lowercase for case-insensitive comparison
    search_skills = {skill.lower() for skill in skills}
    
    # Find resumes that have ALL the requested skills
    matching_resumes = []
    
    for resume_id, resume_skills in RESUME_SKILL_MAPPING.items():
        # Convert resume skills to lowercase
        lower_resume_skills = {skill.lower() for skill in resume_skills}
        
        # Check if all search skills exist in this resume's skills
        if search_skills.issubset(lower_resume_skills):
            matching_resumes.append({
                "resume_id": resume_id,
                "skills": list(resume_skills)  # Return the original case skills
            })
    
    return matching_resumes
    
@app.get("/resumes/skills")
def get_all_skills():
    return {"skills": sorted(list(GLOBAL_SKILLS))}


@app.get("/resumes/{resume_id}/download")
def download_resume(
    resume_id: str,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")
    
    if not os.path.exists(resume.file_path):
        raise HTTPException(404, detail="File not found")
    
    return FileResponse(
        resume.file_path,
        media_type="application/pdf",
        filename=resume.filename
    )

@app.get("/resumes/{resume_id}/analyze", response_model=ResumeAnalysisResponse)
async def analyze_resume(
    resume_id: str,
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Resume not found")

    try:
        text = extract_text_from_pdf(resume.file_path, max_pages=3)
        if not text:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No text could be extracted from the PDF"
            )
        
        entities = extract_resume_entities(text[:])
        processed_at = datetime.now()
        # Process metadata with improved name cleaning
        contact = entities.get('CONTACT', [['', '']])[0]
        try:
            name = entities.get("NAME", [['']])[0]  # Try NAME first
        except (KeyError, IndexError):  # If NAME missing or empty
            try:
                name = entities.get("ORG", [''])[0][:14] # Fall back to ORG
            except (KeyError, IndexError):  # If ORG missing or empty
                name = ""  # Final fallback
        
        # Process skills with tracking
        raw_skills = entities.get('SKILLS', [[]])[0]
        skills = track_skills(resume_id, raw_skills)
        
        # Process experience
        experience = extract_experience_details(text)
        # Process education
        edu_entries = entities.get('EDUCATION', [[]])[0]
        education = extract_education_details(edu_entries, entities.get('DATE', []))
        
        # Process projects
        projects = extract_projects(text)
        final_projects = []
        for project in projects:
            final_projects.append(_finalize_project(project))
        
        result = {
            "metadata": {
                "name": name,
                "email": contact[0] if len(contact) > 0 else "",
                "phone": contact[1] if len(contact) > 1 else ""
            },
            "skills": get_filtered_skills(resume_id),  # Use filtered skills
            "experience": experience,
            "education": education,
            "projects": final_projects,
            "processed_at": processed_at.isoformat()
        }

        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resume analysis service unavailable"
        )

@app.post("/resumes/{resume_id}/store-analysis", response_model=ResumeAnalysisResponse)
def store_analysis(
    resume_id: str,
    db: Session = Depends(get_db)
):
    """Store analyzed resume data"""
    analysis_data = analyze_resume(resume_id, db)
    
    # Store in database
    db_analysis = ResumeAnalysis(
        resume_id=resume_id,
        analysis_data=analysis_data,
        tags=extract_tags(analysis_data)  # Auto-generate tags
    )
    
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    
    return db_analysis

@app.get("/resumes/{resume_id}", response_model=ResumeResponse)
def get_resume_metadata(
    resume_id: str,
    db: Session = Depends(get_db)
):
    """Get resume metadata"""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")
    
    return ResumeResponse(
        **resume.__dict__,
        download_url=f"/resumes/{resume.id}/download"
    )

@app.delete("/resumes/{resume_id}")
def delete_resume(
    resume_id: str,
    db: Session = Depends(get_db)
):
    """Delete a resume from both storage and database"""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(404, detail="Resume not found")
    
    try:
        # Delete file first
        if os.path.exists(resume.file_path):
            os.remove(resume.file_path)
        
        # Then delete from database
        db.delete(resume)
        db.commit()
        return {"message": "Resume deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Delete failed for {resume_id}: {str(e)}", exc_info=True)
        raise HTTPException(500, detail="Failed to delete resume")

# FUTURE PLAN
# @app.get("/resumes/{resume_id}/analyze")
# def analyze_resume(
#     resume_id: str,
#     db: Session = Depends(get_db)
# ):
#     """Analyze resume content with locally loaded LLM"""
#     resume = db.query(Resume).filter(Resume.id == resume_id).first()
#     if not resume:
#         raise HTTPException(404, detail="Resume not found")
#     try:
#         # Read and extract text from PDF
#         with open(resume.file_path, "rb") as f:
#             pdf_reader = PyPDF2.PdfReader(BytesIO(f.read()))
#             text = "\n".join([page.extract_text() for page in pdf_reader.pages])
        
#         # Create prompt for the LLM
#         prompt = f"""
#         Analyze the following resume and extract structured information:
        
#         {text}
        
#         Return JSON format with:
#         - name
#         - email
#         - phone
#         - skills (array)
#         - experience (array of objects with: company, role, duration, description)
#         - education (array of objects with: institution, degree, year)
#         """
        
#         # Generate analysis
#         inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
#         with torch.no_grad():
#             outputs = model.generate(**inputs, max_new_tokens=1000)
        
#         # Decode and parse response
#         analysis = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
#         # Extract JSON part from the response
#         json_start = analysis.find('{')
#         json_end = analysis.rfind('}') + 1
#         json_response = json.loads(analysis[json_start:json_end])
        
#         return {
#             "metadata": {
#                 "name": json_response.get("name"),
#                 "email": json_response.get("email"),
#                 "phone": json_response.get("phone")
#             },
#             "skills": json_response.get("skills", []),
#             "experience": json_response.get("experience", []),
#             "education": json_response.get("education", [])
#         }
        
#     except Exception as e:
#         logger.error(f"Resume analysis failed: {str(e)}", exc_info=True)
#         raise HTTPException(500, detail=f"Resume analysis failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
