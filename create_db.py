# create_db.py
from app.db.session import engine
from app.db.base import Base
from app.models import db_models  # noqa: F401 ensure models are imported

def main():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done.")

if __name__ == "__main__":
    main()
