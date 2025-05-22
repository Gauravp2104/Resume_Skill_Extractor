import re
import logging
from datetime import datetime
from typing import List, Dict, Optional
from io import BytesIO
import PyPDF2
from sqlalchemy.orm import Session
from models import ResumeAnalysis
from database import get_db
import torch
from transformers import pipeline
import logging
from collections import defaultdict
import spacy
import re
from datetime import datetime
from typing import List, Dict, Set

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize NLP model at module level
try:
    nlp_bert = pipeline(
        "ner",
        model="dslim/bert-large-NER", 
        aggregation_strategy="max", 
        device=0 if torch.cuda.is_available() else -1,
        grouped_entities=True 
    )   
    logger.info("NER pipeline initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize NER pipeline: {str(e)}")
    raise

nlp_spacy = spacy.load("en_core_web_lg")

GLOBAL_SKILLS: Set[str] = set()
RESUME_SKILL_MAPPING: Dict[str, Set[str]] = {}

def extract_experience_details(text: str) -> List[Dict]:
    """
    More robust experience extraction from text
    """
    experiences = []
    
    # Split text into sections that might contain experiences
    sections = re.split(r'\n\s*(?:Professional Experience|Work Experience|Experience|Employment History)\s*\n', text, flags=re.IGNORECASE)
    
    if len(sections) > 1:
        experience_text = sections[1]
        
        # Split into individual experience entries
        entries = re.split(r'\n\s*(?=\S.*\n\s*-)', experience_text)
        
        for entry in entries:
            if not entry.strip():
                continue
                
            # Extract role and company
            lines = [line.strip() for line in entry.split('\n') if line.strip()]
            role = ""
            company = ""
            description = []
            
            # First line typically contains role/company
            if lines:
                first_line = lines[0]
                # Handle different formats:
                if ' at ' in first_line:
                    parts = first_line.split(' at ')
                    role = parts[0].strip()
                    company = parts[1].strip()
                elif ' - ' in first_line:
                    parts = first_line.split(' - ')
                    role = parts[0].strip()
                    company = parts[1].strip()
                else:
                    company = first_line.strip()
                    role = "Professional Role"
            
            # Extract duration if present
            duration = ""
            date_matches = re.search(
                r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b)\s*[-–—to]+\s*'
                r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b|\bPresent\b)',
                entry, flags=re.IGNORECASE
            )
            if date_matches:
                duration = f"{date_matches.group(1)} - {date_matches.group(2)}"
            
            # Extract description bullets
            bullets = re.findall(r'(?:•|\d+\.)\s*(.+?)(?=\n\s*(?:•|\d+\.|$))', entry)
            if bullets:
                description = bullets
            else:
                # Fallback to capturing sentences after company
                description_lines = []
                capturing = False
                for line in lines[1:]:
                    if not line.startswith('-') and not line.startswith('•'):
                        if capturing:
                            description_lines.append(line)
                    else:
                        capturing = True
                        description_lines.append(line.lstrip('-• ').strip())
                description = description_lines
            
            experiences.append({
                "role": role,
                "company": company,
                "duration": duration,
                "location": "",
                "description": "\n".join(description)
            })
    
    return experiences
    
def extract_education_details(edu_entries: List[str], dates: List[str]) -> List[Dict]:
    """
    Extract structured education information
    """
    education = []
    degree_pattern = re.compile(
        r'(Bachelor|B\.?Tech|Master|M\.?Tech|Ph\.?D|Doctorate|Diploma|Associate)'
        r'[\s\.]*(?:of|in)?[\s\.]*(?:Science|Arts|Engineering|Technology|Business|Computer|Information)?'
        r'[\s\.]*(?:and)?[\s\.]*(?:[A-Za-z]+)?', re.IGNORECASE
    )

    for edu in edu_entries:
        degree_match = degree_pattern.search(edu)
        degree = degree_match.group() if degree_match else "Degree"
        
        institution = degree_pattern.sub('', edu).strip()
        institution = re.sub(r'^in\s+', '', institution, flags=re.IGNORECASE)
        
        year_match = re.search(r'(?:19|20)\d{2}', edu)
        year = year_match.group() if year_match else ""
        
        education.append({
            "degree": degree.strip(),
            "institution": institution.strip(),
            "year": "4 years"
        })

    return education[1:]

def extract_projects(text: str) -> List[Dict]:
    """
    Extract projects with complete descriptions and proper technology mapping
    """
    projects = []
    
    # Normalize different bullet characters and whitespace
    text = re.sub(r'[\-\*‣◦]', '•', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Split by project sections (handling markdown-style headers)
    project_sections = re.split(
        r'\n\s*(?:#{1,3}\s*)?(?:Projects|Personal Projects|Academic Projects|Work Projects|Key Projects)\s*\n',
        text,
        flags=re.IGNORECASE
    )
    
    if len(project_sections) > 1:
        project_text = project_sections[1]
        
        # Split into individual projects using multiple patterns
        project_entries = re.split(
            r'\n\s*(?=\S.*\n\s*(?:•|\d+\.|#|Technologies:|[A-Z][a-z]+ [A-Z][a-z]+:))',
            project_text
        )
        
        current_project = None
        
        for entry in project_entries:
            if not entry.strip():
                continue
                
            lines = [line.strip() for line in entry.split('\n') if line.strip()]
            if not lines:
                continue
                
            # Check if this is a new project heading
            first_line = lines[0]
            is_project_header = (
                len(first_line.split()) <= 10 and  # Reasonable length for project title
                not first_line.startswith('•') and
                not first_line[0].isdigit() and
                not re.match(r'^(Technologies|Tools|Skills):', first_line, re.IGNORECASE)
            )
            
            if is_project_header:
                # Save previous project if exists
                if current_project:
                    projects.append(_finalize_project(current_project))
                
                # Extract project name and date/technologies
                name_parts = re.split(r'[•|:]', first_line, 1)
                name = name_parts[0].strip()
                
                # Extract date range if present in name
                date_match = re.search(
                    r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4} [–-] (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}',
                    name
                )
                date_range = date_match.group() if date_match else ""
                if date_range:
                    name = name.replace(date_range, '').strip()
                
                # Start new project
                current_project = {
                    "name": name,
                    "date_range": date_range,
                    "technologies": "",
                    "description_parts": []
                }
                
                # Process remaining lines
                for line in lines[1:]:
                    if re.match(r'^(Technologies|Tools|Stack):', line, re.IGNORECASE):
                        current_project["technologies"] = line.split(':', 1)[1].strip()
                    elif line.startswith('•'):
                        current_project["description_parts"].append(line[1:].strip())
                    else:
                        # Add as context for the next bullet point
                        if current_project["description_parts"]:
                            current_project["description_parts"][-1] += " " + line
                        else:
                            current_project["description_parts"].append(line)
            else:
                # Continuation of current project's description
                if current_project:
                    for line in lines:
                        if line.startswith('•'):
                            current_project["description_parts"].append(line[1:].strip())
                        elif re.match(r'^(Technologies|Tools|Stack):', line, re.IGNORECASE):
                            current_project["technologies"] = line.split(':', 1)[1].strip()
                        else:
                            if current_project["description_parts"]:
                                current_project["description_parts"][-1] += " " + line
                            else:
                                current_project["description_parts"].append(line)
        
        # Add the last project
        if current_project:
            projects.append(_finalize_project(current_project))
    
    return projects

def _finalize_project(project: Dict) -> Dict:
    """Convert description parts into a coherent description"""
    # Clean up technologies
    technologies = project["technologies"]
    if technologies:
        technologies = re.sub(r'[\s,]+', ', ', technologies).strip(', ')
    
    # Build coherent description
    description_lines = []
    
    # Add date range if exists
    if project["date_range"]:
        description_lines.append(f"Project duration: {project['date_range']}.")
    
    # Process description parts
    for part in project["description_parts"]:
        # Skip lines that are actually skills or other sections
        if re.match(r'^(Technical Skills|Languages|Libraries|Frameworks|Tools|Achievements)', part, re.IGNORECASE):
            continue
        
        # Clean up the description part
        part = re.sub(r'\s+', ' ', part).strip()
        if part:
            # Capitalize first letter and add period if missing
            part = part[0].upper() + part[1:]
            if not part.endswith(('.', '!', '?')):
                part += '.'
            description_lines.append(part)
    
    # Combine into paragraphs (group related sentences)
    description = ""
    current_paragraph = []
    
    for line in description_lines:
        # Start new paragraph if current one is getting long
        if len(current_paragraph) >= 3 or (current_paragraph and len(' '.join(current_paragraph + [line]))) > 150:
            description += ' '.join(current_paragraph) + "\n\n"
            current_paragraph = []
        current_paragraph.append(line)
    
    # Add the last paragraph
    if current_paragraph:
        description += ' '.join(current_paragraph)
    
    return {
        "name": project["name"],
        "description": description.strip(),
        "technologies": technologies
    }
    

def _finalize_project(project: Dict) -> Dict:
    """Convert description parts into a coherent description"""
    # Clean up technologies
    technologies = project["technologies"]
    if technologies:
        technologies = re.sub(r'[\s,]+', ', ', technologies).strip(', ')
    
    # Build coherent description
    description_lines = []
    for part in project["description_parts"]:
        # Skip lines that are actually skills or other sections
        if re.match(r'^(Technical Skills|Languages|Libraries|Frameworks|Tools)', part, re.IGNORECASE):
            continue
        
        # Clean up the description part
        part = re.sub(r'\s+', ' ', part).strip()
        if part:
            # Capitalize first letter and add period if missing
            part = part[0].upper() + part[1:]
            if not part.endswith(('.', '!', '?')):
                part += '.'
            description_lines.append(part)
    
    # Combine into paragraphs (group 2-3 related sentences)
    description = ""
    i = 0
    while i < len(description_lines):
        # Take 2-3 sentences that seem related
        group = description_lines[i:i+3]
        if len(group) > 1 and all(len(s.split()) < 20 for s in group):
            description += " ".join(group) + "\n\n"
            i += 3
        else:
            description += group[0] + "\n\n"
            i += 1
    
    return {
        "name": project["name"],
        "description": description.strip(),
        "technologies": technologies
    }

def clean_skills(skills: List[str]) -> List[str]:
    """
    Strictly filter only technical skills
    """
    technical_skills = {
        # Programming Languages
        'python', 'java', 'javascript', 'c++', 'c#', 'go', 'ruby', 'swift', 'kotlin', 
        'typescript', 'php', 'rust', 'scala', 'r', 'dart', 'sql',
        
        # Web Technologies
        'html', 'css', 'react', 'angular', 'vue', 'django', 'flask', 'spring', 
        'laravel', 'node.js', 'express', 'asp.net',
        
        # Data/Database
        'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sqlite', 'firebase',
        'pandas', 'numpy', 'spark', 'hadoop', 'tensorflow', 'pytorch', 'keras',
        
        # DevOps/Cloud
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'ansible',
        'jenkins', 'git', 'linux', 'bash',
        
        # Mobile
        'android', 'ios', 'react native', 'flutter', 'xamarin',
        
        # Other technical terms
        'machine learning', 'artificial intelligence', 'deep learning', 'nlp',
        'computer vision', 'blockchain', 'cybersecurity', 'embedded systems',
        'arduino', 'raspberry pi'
    }
    
    cleaned = []
    seen = set()
    
    for skill in skills:
        # Basic cleaning
        skill = re.sub(r'[^a-zA-Z0-9+#\.\s]', '', skill).strip().lower()
        
        # Check if it's a technical skill or common variation
        if skill in technical_skills:
            proper_case = skill.title() if len(skill) > 3 else skill.upper()
            if proper_case not in seen:
                seen.add(proper_case)
                cleaned.append(proper_case)
        else:
            # Check for known variations (e.g., "js" -> "JavaScript")
            variations = {
                'js': 'JavaScript',
                'reactjs': 'React',
                'nodejs': 'Node.js',
                'ai': 'Artificial Intelligence',
                'ml': 'Machine Learning',
                'dl': 'Deep Learning'
            }
            if skill in variations and variations[skill] not in seen:
                seen.add(variations[skill])
                cleaned.append(variations[skill])
    
    return sorted(cleaned)

def extract_text_from_pdf(file_path: str, max_pages: int = 3) -> str:
    """Extract text from PDF with page limit"""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(BytesIO(f.read()))
            return "\n".join(
                page.extract_text() 
                for i, page in enumerate(reader.pages) 
                if i < max_pages and page.extract_text()
            )
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        return ""

def process_bert_entities(results):
    """Process BERT NER results"""
    entity_map = {
        'PER': ['PER'],
        'ORG': ['ORG'],
        'LOC': ['LOC'],
        'DATE': ['DATE']
    }
    
    entities = defaultdict(list)
    current_entity = None
    
    for entity in results:
        entity_group = None
        for group, labels in entity_map.items():
            if entity['entity_group'] in labels:
                entity_group = group
                break
        
        if entity_group:
            if entity['word'].startswith('##'):
                if current_entity and current_entity['group'] == entity_group:
                    current_entity['text'] += entity['word'].replace('##', '')
            else:
                if current_entity:
                    entities[current_entity['group']].append(current_entity['text'])
                current_entity = {
                    'text': entity['word'],
                    'group': entity_group
                }
    
    if current_entity:
        entities[current_entity['group']].append(current_entity['text'])
    
    return dict(entities)

def process_spacy_entities(doc):
    """Process spaCy entities"""
    entities = defaultdict(list)
    for ent in doc.ents:
        if ent.label_ == 'PERSON':
            entities['PER'].append(ent.text)
        elif ent.label_ == 'ORG':
            entities['ORG'].append(ent.text)
        elif ent.label_ == 'GPE' or ent.label_ == 'LOC':
            entities['LOC'].append(ent.text)
        elif ent.label_ == 'DATE':
            entities['DATE'].append(ent.text)
    
    return dict(entities)

def extract_names(text, entities):
    # Look for name patterns at the beginning
    name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
    
    if not name_match:
        return []
    
    # Clean and format the name
    name = name_match.group(1)
    cleaned_name = re.sub(r'[^\w\s]', '', name)  # Remove special chars
    cleaned_name = ' '.join(word.capitalize() for word in cleaned_name.split())
    entities['NAME'].append(cleaned_name)

def extract_contact_info(text, entities):
    """Extract emails, phones, links"""
    contacts = []
    emails = re.findall(r'[\w\.-]+@[\w\.-]+', text)
    phones = re.findall(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', text)
    links = re.findall(r'https?://[^\s]+|www\.[^\s]+', text)
    
    contacts.extend(emails)
    contacts.extend(phones)
    contacts.extend(links)
    entities['CONTACT'].append(contacts)

def extract_education(text, entities):
    """Extract education information"""
    education = []
    # Match degree patterns
    degrees = re.findall(r'(Bachelor|B\.?[Ss]\.?|Master|PhD)\s+(?:of|in)?\s*([A-Za-z\s]+)', text)
    for degree in degrees:
        education.append(f"{degree[0]} in {degree[1]}")
    
    # Match school names
    schools = re.findall(r'([A-Z][a-zA-Z\s]+(?:Institute|University|School|College)[a-zA-Z\s]*)', text)
    education.extend(schools)
    entities['EDUCATION'].append(education)

def extract_skills(text, entities):
    """Extract technical skills"""
    skills = []
    # Match skills section if exists
    skill_section = re.search(r'Technical Skills.*?:([\s\S]+?)(?:\n\n|$)', text, re.IGNORECASE)
    if skill_section:
        skills_text = skill_section.group(1)
        skills.extend(re.findall(r'[A-Za-z\+#\.]+', skills_text))
    
    # Common tech skills
    tech_terms = ['Python', 'Java', 'SQL', 'JavaScript', 'TensorFlow', 'Django']
    skills.extend([term for term in tech_terms if term in text])
    entities['SKILLS'].append(list(set(skills)))
    # Remove duplicates

def extract_experience_section(text: str) -> str:
    """Extract the experience section from resume text"""
    # Look for common section headers
    section_pattern = r'(?:Experience|Work\s*History|Employment)[\s\S]+?(?=(?:\n\s*\n[A-Z][a-z]+:)|$)'
    match = re.search(section_pattern, text, re.IGNORECASE)
    return match.group(0) if match else text  # Fallback to full text if section not found

def clean_company_name(company: str) -> str:
    """Clean and normalize company names"""
    company = re.sub(r'[^\w\s&]', '', company)  # Remove special chars except &
    company = re.sub(r'\s+', ' ', company).strip()
    return company.title()

def clean_role_name(role: str) -> str:
    """Clean and normalize role names"""
    role = re.sub(r'[^\w\s]', '', role)  # Remove special chars
    role = re.sub(r'\s+', ' ', role).strip()
    return role.title()

def extract_experience_description(text: str, start_pos: int) -> List[str]:
    """Extract bullet points from experience description"""
    remaining_text = text[start_pos:]
    bullets = re.findall(r'•\s*(.+?)(?=\n\s*(?:•|[A-Z]|\d|$))', remaining_text, re.DOTALL)
    return [b.strip() for b in bullets[:3]]  # Return max 3 bullet points

def extract_experience_with_duration(text: str, entities: Dict) -> List[Dict]:
    """Enhanced experience extraction focusing on experience section"""
    # First identify the experience section
    experience_section = extract_experience_section(text)
    if not experience_section:
        return []
    
    # Improved pattern to capture experience entries
    pattern = r"""
        (?P<role>[A-Z][a-zA-Z\s]+?)                # Job role
        \s*(?:at|@|\||\||in|,)\s*                  # Separator
        (?P<company>[A-Z][a-zA-Z\s&]+?)            # Company name
        \s*
        (?P<duration>                               # Duration
            (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4} 
            \s*[-–]\s* 
            (?:Present|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})
        )
        \s*
        (?:•\s*(?P<description>.+?)(?=\n\s*(?:•|[A-Z]|\d)))  # Bullet points
    """
    
    experiences = []
    for match in re.finditer(pattern, experience_section, re.VERBOSE | re.IGNORECASE | re.DOTALL):
        exp = match.groupdict()
        
        # Extract bullet points if they exist
        description = []
        if exp['description']:
            description.append(exp['description'].strip())
            # Look for additional bullet points
            next_bullets = re.findall(r'•\s*(.+?)(?=\n\s*(?:•|[A-Z]|\d|$))', 
                                    text[match.end():], re.DOTALL)
            description.extend([b.strip() for b in next_bullets[:3]])
        
        experiences.append({
            "company": clean_company_name(exp.get("company", "")),
            "role": clean_role_name(exp.get("role", "")),
            "duration": exp.get("duration", "").strip(),
            "description": description
        })
    
    entities['EXPERIENCE'].append(experiences)

def clean_name(name: str) -> str:
    """
    Improved name cleaning with multiple fallback strategies
    """
    if not name:
        return "Unknown"
    
    # First try: Remove all special characters except spaces and hyphens
    clean = re.sub(r'[^a-zA-Z\s-]', '', name).strip()
    if clean and len(clean.split()) >= 2:
        return clean
    
    # Second try: Extract from email if available
    if '@' in name:
        email_part = name.split('@')[0]
        if '.' in email_part:
            return ' '.join([part.capitalize() for part in email_part.split('.')])
    
    # Third try: Take first two title-cased words
    words = [w.capitalize() for w in re.findall(r'[a-zA-Z]+', name)[:1]]
    return ' '.join(words) if words else "Unknown"

def normalize_skills(skills: List[str]) -> List[str]:
    """
    Normalize skills with comprehensive mapping and tracking
    """
    skill_mappings = {
        # Standardizations
        'SQL': 'sql',
        'mysql': 'sql',
        'javascript': 'JavaScript',
        'html': 'HTML',
        'css': 'CSS',
        'qjango': 'Django',
        'c++': 'C++',
        'java': 'Java',
        'python': 'Python',
        'numpy': 'NumPy',
        'tensorflow': 'TensorFlow',
        
        # Common aliases
        'js': 'JavaScript',
        'reactjs': 'React',
        'nodejs': 'Node.js',
        'ai': 'Artificial Intelligence',
        'ml': 'Machine Learning',
        'dl': 'Deep Learning',
        'sqlite': 'SQL',
        'postgresql': 'SQL',
        'oracle': 'SQL',
        'mongodb': 'NoSQL'
    }
    
    normalized = set()
    for skill in skills:
        # Basic cleaning
        skill = re.sub(r'[^a-zA-Z0-9+#\.\s]', '', skill).strip().lower()
        if not skill or len(skill) < 2:
            continue
        
        # Apply mappings
        skill = skill_mappings.get(skill, skill)
        
        # Standardize capitalization
        if skill.upper() == skill and len(skill) > 2:
            skill = skill.title()
        elif '.' in skill:  # Handle things like Node.js
            parts = skill.split('.')
            skill = f"{parts[0].title()}.{parts[1]}" if len(parts) > 1 else skill
        
        normalized.add(skill)
    
    return sorted(normalized, key=lambda x: x.lower())

def track_skills(resume_id: str, skills: List[str]):
    """
    Track skills globally and per-resume
    """
    skill_set = set()
    technical_skills = [
        # Programming Languages
        'python', 'java', 'javascript', 'c++', 'c#', 'go', 'ruby', 'swift', 'kotlin', 
        'typescript', 'php', 'rust', 'scala', 'r', 'dart', 'sql',
        
        # Web Technologies
        'html', 'css', 'react', 'angular', 'vue', 'django', 'flask', 'spring', 
        'laravel', 'node.js', 'express', 'asp.net',
        
        # Data/Database
        'mysql', 'postgresql', 'mongodb', 'redis', 'oracle', 'sqlite', 'firebase',
        'pandas', 'numpy', 'spark', 'hadoop', 'tensorflow', 'pytorch', 'keras',
        
        # DevOps/Cloud
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform', 'ansible',
        'jenkins', 'git', 'linux', 'bash',
        
        # Mobile
        'android', 'ios', 'react native', 'flutter', 'xamarin',
        
        # Other technical terms
        'machine learning', 'artificial intelligence', 'deep learning', 'nlp',
        'computer vision', 'blockchain', 'cybersecurity', 'embedded systems',
        'arduino', 'raspberry pi'
    ]

    final_normalized = []
    normalized = normalize_skills(skills)

    for i in normalized:
        if i.lower() in technical_skills:
            final_normalized.append(i)
            skill_set.add(i)
    
    # Update global skills
    GLOBAL_SKILLS.update(skill_set)
    
    # Update resume mapping
    RESUME_SKILL_MAPPING[resume_id] = skill_set
    
    return final_normalized
    
def get_filtered_skills(resume_id: str) -> List[str]:
    """
    Get skills filtered by global knowledge
    """
    resume_skills = RESUME_SKILL_MAPPING.get(resume_id, set())
    return sorted(resume_skills & GLOBAL_SKILLS)  # Intersection with global skills


def extract_resume_entities(text):

    # Clean text first
    text = re.sub(r'\s+', ' ', text).strip()
    
    entities = {
        'NAME': [],
        'CONTACT': [],
        'EDUCATION': [],
        'EXPERIENCE': [],
        'SKILLS': [],
        'PROJECTS': [],
        'ORGANIZATIONS': [],
        'DATES': [],
        'LOCATIONS': []
    }
    
    try:
        # Extract using BERT
        bert_results = nlp_bert(text)
        entities.update(process_bert_entities(bert_results))
        
        # Extract using spaCy
        doc = nlp_spacy(text)
        entities.update(process_spacy_entities(doc))
        
        extract_names(text, entities)
        extract_contact_info(text, entities)
        extract_education(text, entities)
        extract_skills(text, entities)
        extract_experience_with_duration(text, entities)

        # Specialized extraction for resumes
        # entities.update({
        #     'NAME': extract_names(text),
        #     'CONTACT': extract_contact_info(text),
        #     'EDUCATION': extract_education(text),
        #     'SKILLS': extract_skills(text),
        #     'EXPERIENCE': extract_experience_with_duration(text, entities),
        # })
        
    except Exception as e:
        print(f"Entity extraction failed: {str(e)}")
    
    return entities


def extract_tags(result: dict) -> List[str]:
    """Generate tags from analysis results"""
    tags = []
    logger.info(result['experience'])
    if result.get('skills'):
        tags.extend(result['skills'][:3])
    if result.get('experience'):
        tags.extend(exp['role'].split()[0] for exp in result['experience'][:2])
    if result.get('education'):
        tags.append(result['education'][0]['degree'].split()[0])
    return list(set(tags))[:5]


def extract_skills_with_context(text: str, entities: dict) -> List[str]:
    """Skill extraction with context awareness"""
    skills_db = load_skills_database()
    found_skills = []
    
    # 1. Direct matches from skills database
    found_skills.extend(
        skill for skill in skills_db 
        if re.search(rf'\b{re.escape(skill)}\b', text, re.IGNORECASE)
    )
    
    # 2. Extract from "Skills" section if exists
    skills_section = extract_section(text, "skills")
    if skills_section:
        found_skills.extend(
            skill for skill in skills_db 
            if skill.lower() in skills_section.lower()
        )
    
    # 3. Add technologies from experience
    tech_keywords = ["Python", "Java", "SQL", "React", "AWS"]
    found_skills.extend(
        tech for tech in tech_keywords 
        if tech in text and tech not in found_skills
    )
    
    return sorted(list(set(found_skills)))

def extract_education_info(text: str) -> List[Dict]:
    """Extract education information with degree parsing"""
    education = []
    degree_pattern = r'(?:Bachelor|B\.?S\.?|Master|M\.?S\.?|Ph\.?D\.?)\s*(?:in|of)?\s*([\w\s]+)'
    
    for match in re.finditer(degree_pattern, text, re.IGNORECASE):
        education.append({
            "degree": match.group(0).strip(),
            "institution": "University",  # Can be enhanced with university extraction
            "year": extract_graduation_year(text)
        })
    
    return education[:3]

def get_best_name_candidate(names: List[str]) -> str:
    if not names:
        return ""
    
    # Find the most likely name candidate
    best_name = max(names, key=lambda x: len(x.split()))
    
    # Clean up the name - remove special characters and extra info
    clean_name = re.sub(r'[^a-zA-Z\s\-]', '', best_name)  # Keep letters, spaces, and hyphens
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()  # Normalize spaces
    
    # Take just the first part if it's messy
    if '/' in clean_name or '|' in clean_name:
        parts = re.split(r'[/|]', clean_name)
        clean_name = parts[0].strip()
    
    # If still too long, take first two words
    if len(clean_name.split()) > 3:
        clean_name = ' '.join(clean_name.split()[:3])
    
    return clean_name or "Unknown"

def store_analysis_result(db: Session, resume_id: str, result: dict):
    try:
        # Convert datetime objects to strings for JSON serialization
        serializable_result = {
            **result,
            'processed_at': result.get('processed_at').isoformat() if result.get('processed_at') else None
        }
        
        analysis = ResumeAnalysis(
            resume_id=resume_id,
            analysis_data=serializable_result,
            tags=extract_tags(result),
            created_at=datetime.now(),
            processed_at=result.get('processed_at')
        )
        
        db.add(analysis)
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store analysis: {str(e)}", exc_info=True)
        raise
