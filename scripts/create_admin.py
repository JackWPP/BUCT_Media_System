"""
Create initial admin user script
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.database import AsyncSessionLocal
from app.crud.user import get_user_by_email, create_user
from app.schemas.user import UserCreate


async def create_admin():
    """Create initial admin user"""
    admin_email = "admin@buct.edu.cn"
    admin_password = "admin123"
    admin_name = "System Administrator"
    
    async with AsyncSessionLocal() as db:
        # Check if admin already exists
        existing_admin = await get_user_by_email(db, admin_email)
        if existing_admin:
            print(f"Admin user already exists: {admin_email}")
            return
        
        # Create admin user
        admin_user = UserCreate(
            email=admin_email,
            password=admin_password,
            full_name=admin_name
        )
        
        db_admin = await create_user(db, admin_user, role="admin")
        print(f"Admin user created successfully!")
        print(f"Email: {db_admin.email}")
        print(f"Password: {admin_password}")
        print(f"Role: {db_admin.role}")
        print("\nPlease change the default password after first login!")


if __name__ == "__main__":
    print("Creating initial admin user...")
    asyncio.run(create_admin())
