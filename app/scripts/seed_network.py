import uuid
from app.db.tigergraph import get_tg_connection, upsert_vertex, upsert_edge
from app.core.security import get_password_hash

def seed_network():
    # User 1 ID provided by user/logs
    USER_1_ID = "27ddd55d-1fde-429e-9b73-cf7c70a31219"
    
    # Common password for all dummy users
    PASSWORD = "Password123!"
    hashed_pw = get_password_hash(PASSWORD)
    
    # Dummy Users Data
    users = [
        {
            "id": str(uuid.uuid4()),
            "name": "Alice Chen",
            "email": "alice@example.com",
            "company_id": "comp_google",
            "role": "Senior Frontend Developer",
            "skills": ["5"], # React
            "follows_user_1": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Bob Smith",
            "email": "bob@example.com",
            "company_id": "comp_meta",
            "role": "Backend Lead",
            "skills": ["6"], # Node.js
            "follows_user_1": True
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Charlie Day",
            "email": "charlie@example.com",
            "company_id": "comp_stripe",
            "role": "Data Scientist",
            "skills": ["10"], # SQL
            "follows_user_1": False
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Diana Prince",
            "email": "diana@example.com",
            "company_id": "comp_netflix",
            "role": "Mobile Developer",
            "skills": ["16"], # Flutter
            "follows_user_1": True
        }
    ]
    
    conn = get_tg_connection()
    
    print(f"--- Seeding {len(users)} Network Users ---")
    
    for u in users:
        # Create User vertex
        print(f"Creating user: {u['name']} ({u['email']})")
        upsert_vertex(
            "User",
            u["id"],
            attributes={
                "userId": u["id"],
                "name": u["name"],
                "email": u["email"],
                "hashed_password": hashed_pw,
                "bio": f"Hi, I'm {u['name']}, a {u['role']}!",
                "resume_text": ""
            }
        )
        
        # Link to Company
        print(f"  Linking to company: {u['company_id']} as {u['role']}")
        upsert_edge(
            "User", u["id"],
            "WORKS_AT",
            "Company", u["company_id"],
            attributes={"role": u["role"], "is_current": True}
        )
        
        # Link to Skills
        for skill_id in u["skills"]:
            print(f"  Adding skill: {skill_id}")
            upsert_edge(
                "User", u["id"],
                "HAS_SKILL",
                "Skill", skill_id,
                attributes={"proficiency": 0.85}
            )
            
        # Follow User 1 if specified
        if u["follows_user_1"]:
            print(f"  Following User 1 ({USER_1_ID})")
            upsert_edge(
                "User", u["id"],
                "FOLLOWS",
                "User", USER_1_ID
            )
            
    print("\n--- Seeding Complete ---")
    print(f"Credentials for all users: Password is {PASSWORD}")
    for u in users:
        print(f"- {u['name']}: {u['email']}")

if __name__ == "__main__":
    seed_network()
