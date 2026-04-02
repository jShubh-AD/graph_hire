import json
import random
from datetime import datetime, timedelta

def generate_data():
    companies = [
        "comp_google", "comp_meta", "comp_stripe", "comp_netflix", "comp_airbnb", 
        "comp_uber", "comp_openai", "comp_anthropic", "comp_datadog", "comp_snowflake"
    ]
    
    company_names = {
        "comp_google": "Google",
        "comp_meta": "Meta",
        "comp_stripe": "Stripe",
        "comp_netflix": "Netflix",
        "comp_airbnb": "Airbnb",
        "comp_uber": "Uber",
        "comp_openai": "OpenAI",
        "comp_anthropic": "Anthropic",
        "comp_datadog": "Datadog",
        "comp_snowflake": "Snowflake"
    }

    skills = {
        "Python": 1, "Java": 3, "JavaScript": 4, "React": 5, "Node.js": 6, 
        "AWS": 7, "Docker": 8, "Kubernetes": 9, "SQL": 10, "NoSQL": 11, 
        "Machine Learning": 12, "TypeScript": 13, "Go": 14, "Rust": 15,
        "Flutter": 16, "Swift": 17, "Kotlin": 18, "PyTorch": 19, "TensorFlow": 20, "Figma": 21
    }

    job_templates = [
        {"title": "Senior Backend Engineer", "skills": ["Python", "Go", "SQL", "Docker", "AWS"], "type": "Backend"},
        {"title": "Frontend Developer", "skills": ["JavaScript", "React", "TypeScript", "Figma"], "type": "Frontend"},
        {"title": "Fullstack Software Engineer", "skills": ["TypeScript", "React", "Node.js", "NoSQL", "AWS"], "type": "Fullstack"},
        {"title": "Mobile App Developer (Flutter)", "skills": ["Flutter", "Dart", "Figma"], "type": "Mobile"},
        {"title": "iOS Engineer", "skills": ["Swift", "Figma"], "type": "Mobile"},
        {"title": "Android Developer", "skills": ["Kotlin", "Java", "Figma"], "type": "Mobile"},
        {"title": "Machine Learning Engineer", "skills": ["Python", "Machine Learning", "PyTorch", "TensorFlow", "SQL"], "type": "AI"},
        {"title": "DevOps Architect", "skills": ["Docker", "Kubernetes", "AWS", "Go", "Python"], "type": "DevOps"},
        {"title": "Data Scientist", "skills": ["Python", "SQL", "Machine Learning", "TensorFlow"], "type": "Data"},
        {"title": "Security Engineer", "skills": ["Python", "Go", "Network Security", "Cloud Security"], "type": "Security"},
        {"title": "Site Reliability Engineer", "skills": ["Python", "Go", "Kubernetes", "Docker", "AWS"], "type": "DevOps"},
        {"title": "Senior React Developer", "skills": ["React", "TypeScript", "JavaScript", "Figma"], "type": "Frontend"},
        {"title": "Rust Systems Programmer", "skills": ["Rust", "Go"], "type": "Backend"},
        {"title": "Fintech Backend Developer", "skills": ["Java", "SQL", "NoSQL", "AWS"], "type": "Backend"},
        {"title": "AI Research Scientist", "skills": ["Python", "PyTorch", "Machine Learning"], "type": "AI"},
    ]

    job_posts = []
    posted_by_edges = []
    requires_skill_edges = []

    start_date = datetime(2024, 3, 1)
    
    for i in range(1, 41):
        job_id = f"job_{i:03d}"
        template = random.choice(job_templates)
        company_id = random.choice(companies)
        
        # Adjust pay based on seniority
        is_senior = "Senior" in template["title"] or "Architect" in template["title"] or "Lead" in template["title"]
        pay_min = random.randint(140, 180) if is_senior else random.randint(100, 140)
        pay_max = pay_min + random.randint(20, 60)
        
        post_date = start_date + timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
        
        job_posts.append({
            "jobId": job_id,
            "title": template["title"],
            "description": f"We are looking for a {template['title']} to join our team at {company_names[company_id]}. "
                           f"You will work on cutting-edge {template['type']} technologies and help us build scalable solutions.",
            "pay_min": float(pay_min * 1000),
            "pay_max": float(pay_max * 1000),
            "job_type": random.choice(["Full-time", "Contract", "Remote"]),
            "duration": random.choice(["Permanent", "6 months", "1 year"]),
            "date_posted": post_date.strftime("%Y-%m-%d %H:%M:%S"),
            "company_name": company_names[company_id],
            "status": "Open",
            "flag_count": 0,
            "is_flagged": False
        })
        
        posted_by_edges.append({
            "source_id": job_id,
            "target_id": company_id
        })
        
        selected_skills = template["skills"]
        # Filter selected skills to only include those in our 'skills' dict
        valid_skills = [s for s in selected_skills if s in skills]
        
        for skill_name in valid_skills:
            requires_skill_edges.append({
                "source_id": job_id,
                "target_id": str(skills[skill_name]),
                "importance": round(random.uniform(0.6, 1.0), 2)
            })

    with open("jobs_data.json", "w") as f:
        json.dump({
            "job_posts": job_posts,
            "posted_by": posted_by_edges,
            "requires_skill": requires_skill_edges
        }, f, indent=4)
    
    print("Jobs data generated successfully in jobs_data.json")

if __name__ == "__main__":
    generate_data()

