# Resume_Skill_Extractor
A web interface allowing candidate resumes to be filtered on a skill basis

## 🚀 Features

### Frontend
- 🔍 Multi-skill search with autocomplete
- 📱 Responsive Material-UI design
- 🔄 Real-time filtering
- 🎨 Visual skill highlighting
- ⏳ Loading indicators
- 🚨 Error handling

### Backend
- ⚡ FastAPI REST endpoints
- 🔎 Case-insensitive skill matching
- 🏎️ Optimized search performance
- 📊 API documentation (Swagger UI)

## 🛠️ Tech Stack

| Frontend          | Backend         |
|-------------------|-----------------|
| React 18          | FastAPI         |
| Material-UI       | Python 3.9+     |
| React Router 6    | Uvicorn         |
| Axios             | Docker          |

## 🏁 Getting Started

### Prerequisites
- Node.js 16+
- Python 3.9+
- Docker (optional)

### 🖥️ Local Development

#### Backend Setup
```bash
cd backend
python -m venv venv
# Linux/Mac:
source venv/bin/activate
# Windows:
.\venv\Scripts\activate

pip install -r requirements.txt
uvicorn main:app --reload
