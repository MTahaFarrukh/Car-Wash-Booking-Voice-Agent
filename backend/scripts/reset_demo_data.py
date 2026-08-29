"""Clear transactional demo data so new bookings are obvious in admin.

Keeps catalog + admin access:
  - services, availability, admin_users (and legacy users table)

Removes:
  - call_logs, bookings, whatsapp_processed_messages, vehicles, customers

Run from backend/ with venv active:

  python -m scripts.reset_demo_data --confirm

Optional: re-insert a tiny seed set after wipe:

  python -m scripts.reset_demo_data --confirm --reseed

WARNING: This deletes real customer/booking data. Only use on a demo/staging DB,
or when you intentionally want a clean slate before recording.
"""

from __future__ import annotations

import argparse

from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.models.booking import Booking
from app.models.call_log import CallLog
from app.models.customer import Customer
from app.models.service import Service
from app.models.vehicle import Vehicle
from app.models.whatsapp_message import WhatsAppProcessedMessage


def _count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def reset_demo_data(*, reseed: bool = False) -> None:
    db = SessionLocal()
    try:
        before = {
            "bookings": _count(db, Booking),
            "customers": _count(db, Customer),
            "call_logs": _count(db, CallLog),
        }
        print("Before:", before)

        db.execute(delete(CallLog))
        db.execute(delete(Booking))
        db.execute(delete(WhatsAppProcessedMessage))
        db.execute(delete(Vehicle))
        db.execute(delete(Customer))
        db.commit()

        after = {
            "bookings": _count(db, Booking),
            "customers": _count(db, Customer),
            "services": _count(db, Service),
            "call_logs": _count(db, CallLog),
        }
        print("After:", after)

        if reseed:
            from scripts.seed import run_seed

            print("Running scripts.seed …")
            run_seed()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Wipe bookings/customers for a clean admin demo")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required — without this flag the script will not delete anything",
    )
    parser.add_argument(
        "--reseed",
        action="store_true",
        help="After wipe, run scripts.seed to restore catalog + sample rows",
    )
    args = parser.parse_args()
    if not args.confirm:
        print("Refusing to run without --confirm (this deletes bookings and customers).")
        raise SystemExit(1)
    reset_demo_data(reseed=args.reseed)
    print("Done. Create one fresh booking on /book, then open /admin.")


if __name__ == "__main__":
    main()
