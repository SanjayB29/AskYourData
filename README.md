# Ask Your Data

**Ask Your Data** is a Natural Language → Dashboard generator. Upload CSV/JSON data, ask questions in plain English, and get tables or charts as results — powered by LLMs, FastAPI, and React.

---

## 🧱 Tech Stack

- **Backend**: FastAPI, MongoDB, Pandas, Matplotlib, Plotly, Seaborn, LLM (Gemini or compatible)
- **Frontend**: React (Create React App)
- **Integration**: Axios for API, Tailwind CSS

---

## ⚙️ Setup Instructions

### 🔧 1. Clone & Setup Environment

```bash
git clone <repo-url>
cd AskYourData-main
python3.11 -m venv venv
source venv/bin/activate
```

### 📦 2. Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
pip install motor==2.5.1 pymongo==3.13.0
```

> Make sure `.env` file is configured with:
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=askyourdata
GEMINI_API_KEY=your_key_here
```

### 🚀 3. Run Backend

```bash
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload
```

- Docs: http://localhost:8000/docs
- API Root: http://localhost:8000/

---

### 🌐 4. Frontend Setup

```bash
cd frontend
npm install --force
npm start
```

- App runs at: http://localhost:3000 (or `3001+` if port is in use)

---