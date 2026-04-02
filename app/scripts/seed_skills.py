import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.db.tigergraph import ensure_skill_exists
from app.core.logger import logger

COMMON_SKILLS = [
    ("Python", "Programming"),
    ("Java", "Programming"),
    ("JavaScript", "Programming"),
    ("React", "Frontend"),
    ("Node.js", "Backend"),
    ("AWS", "Cloud"),
    ("Docker", "DevOps"),
    ("Kubernetes", "DevOps"),
    ("SQL", "Database"),
    ("NoSQL", "Database"),
    ("Machine Learning", "AI"),
    ("TypeScript", "Programming"),
    ("Go", "Programming"),
    ("Rust", "Programming"),
]

def seed_skills():
    logger.info("Seeding common skills...")
    for name, category in COMMON_SKILLS:
        skill_id = ensure_skill_exists(name, category)
        logger.info(f"Skill '{name}' seeded with ID {skill_id}")
    logger.info("Seeding complete!")

if __name__ == "__main__":
    seed_skills()
