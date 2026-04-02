import sys
import os
import uuid
from datetime import datetime, timezone

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.db.tigergraph import get_tg_connection
from app.core.logger import logger

def seed_jobs():
    conn = get_tg_connection()
    
    # 1. Ensure InnovateTech company exists
    company_id = "comp_innovate"
    conn.upsertVertex("Company", company_id, attributes={
        "name": "InnovateTech",
        "industry": "Software",
        "size": "50-200",
        "flag_count": 0,
        "is_flagged": False
    })
    
    # 2. 4 Dummy Jobs
    # React (ID 5), Python (ID 2), ML (ID 12)
    jobs_data = [
        {"title": "React Frontend Developer", "skills": [4], "status": "Open", "desc": "Looking for a React expert."},
        {"title": "Backend Python Developer", "skills": [1, 11], "status": "Open", "desc": "High-performance Python backend roles."},
        {"title": "Legacy Python Engineer", "skills": [1], "status": "Closed", "desc": "Maintenance of legacy Python systems."},
        {"title": "Machine Learning Engineer", "skills": [10], "status": "Open", "desc": "Deep learning and model optimization."}
    ]
    
    # Wait, I should verify the skill IDs. Let's look up by name to be sure.
    # Actually, I'll just use the name-to-id mapping from the database.
    
    skills_res = conn.getVertices("Skill")
    skill_map = {v["attributes"]["name"]: int(v["v_id"]) for v in skills_res}
    
    logger.info(f"Loaded {len(skill_map)} skills from DB: {skill_map}")
    
    target_jobs = [
        {"title": "React Guru", "skill_name": "React", "status": "Open"},
        {"title": "Python Backend Expert", "skill_name": "Python", "status": "Open"},
        {"title": "Python Support (Finished)", "skill_name": "Python", "status": "Closed"},
        {"title": "ML Researcher", "skill_name": "Machine Learning", "status": "Open"}
    ]

    logger.info("Seeding jobs with unique UUIDs...")
    for j in target_jobs:
        job_id = str(uuid.uuid4())
        sid = skill_map.get(j["skill_name"])
        
        if sid is None:
            logger.warning(f"Skill '{j['skill_name']}' not found. Skipping job '{j['title']}'")
            continue
            
        conn.upsertVertex("JobPost", job_id, attributes={
            "title": j["title"],
            "description": f"Exciting role for a {j['skill_name']} specialist.",
            "company_name": "InnovateTech",
            "job_type": "Full-Time",
            "pay_min": 80000.0,
            "pay_max": 120000.0,
            "status": j["status"],
            "date_posted": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "flag_count": 0,
            "is_flagged": False
        })
        
        # Link to Company
        conn.upsertEdge("JobPost", job_id, "POSTED_BY", "Company", company_id)
        
        # Link to Skill
        conn.upsertEdge("JobPost", job_id, "REQUIRES_SKILL", "Skill", str(sid), attributes={"importance": 1.0})
        
        logger.info(f"Seeded job '{j['title']}' (ID: {job_id}) requiring {j['skill_name']} (ID: {sid}) with status '{j['status']}'")

    logger.info("Dummy jobs seeding complete.")

if __name__ == "__main__":
    seed_jobs()
