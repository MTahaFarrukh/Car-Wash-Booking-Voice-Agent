"""Seed an admin_users row after creating the user in Supabase Auth.

Usage (from backend/ with venv active):

  python -m scripts.seed_admin --email you@example.com --auth-user-id <supabase-uuid>

Create the Auth user first in Supabase Dashboard → Authentication → Users
(email/password). Copy the user's UUID into --auth-user-id.
"""

from __future__ import annotations

import argparse
import uuid

from sqlalchemy import or_, select

from app.core.database import SessionLocal
from app.models.admin_user import AdminUser


def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert an admin_users row")
    parser.add_argument("--email", required=True)
    parser.add_argument("--auth-user-id", required=True, help="Supabase Auth user UUID")
    parser.add_argument("--role", default="ADMIN")
    args = parser.parse_args()

    auth_user_id = uuid.UUID(args.auth_user_id)
    email = args.email.strip().lower()

    db = SessionLocal()
    try:
        existing = db.scalar(
            select(AdminUser).where(
                or_(AdminUser.auth_user_id == auth_user_id, AdminUser.email == email)
            )
        )
        if existing:
            existing.auth_user_id = auth_user_id
            existing.email = email
            existing.role = args.role
            existing.is_active = True
            db.commit()
            print(f"Updated admin: {existing.email} ({existing.id})")
        else:
            row = AdminUser(
                auth_user_id=auth_user_id,
                email=email,
                role=args.role,
                is_active=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            print(f"Created admin: {row.email} ({row.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
