"""Seed the default evaluation criteria (safe to run repeatedly)."""
from database.database import initialize_database, seed_criteria


if __name__ == "__main__":
    initialize_database()
    seed_criteria()
    print("Database initialized and default criteria seeded.")
