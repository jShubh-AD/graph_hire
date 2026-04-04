# GraphHire Backend

AI-powered job matching and professional networking platform leveraging TigerGraph for semantic relationship analysis and Google Gemini for intelligent resume parsing.

## 🚀 Getting Started

### 1. TigerGraph Cloud (Savanna) Setup
GraphHire requires a TigerGraph instance. Follow these steps to set up your database:
1. Create an account on [TigerGraph Cloud](https://tgcloud.io/).
2. Create a new **Starter Kit** or an empty solution (Version 4.1+ recommended).
3. Once the solution is "Ready", go to the **Global Settings** to find your Host URL.
4. Create a **Secret** in the GraphStudio or via GSQL to generate your `TG_SECRET`.
5. Ensure your graph name matches the one in your `.env` (default: `graphhire`).

### 2. Local Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/jShubh-AD/graph_hire.git
   cd graph_hire
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   Copy the example environment file and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` with your TigerGraph host, secret, token, and Gemini API key.*

### 3. Data Seeding
Run the following scripts to populate your graph with initial data:
```bash
# Seed skills library
python -m app.scripts.seed_skills

# Seed dummy job postings
python -m app.scripts.seed_jobs_dummy

# Seed dummy professional network
python -m app.scripts.seed_network
```

### 4. Running the Application
Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`.

## 📖 API Documentation
Once the server is running, you can access the interactive API documentation at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 🛠️ Resources
- [TigerGraph Documentation](https://docs.tigergraph.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Gemini API Docs](https://ai.google.dev/docs)
