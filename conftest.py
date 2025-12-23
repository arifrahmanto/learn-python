import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import Base
from app import app
from models.user import User
from core.security import hash_password

# Gunakan SQLite in-memory untuk testing agar cepat dan terisolasi
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Fixture untuk membuat database bersih setiap kali test function dijalankan"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Fixture untuk Flask Test Client dengan database yang dimock"""
    app.config['TESTING'] = True
    
    # Patch SessionLocal di dalam app.py agar menggunakan session test kita
    with patch('app.SessionLocal', return_value=db_session):
        with app.test_client() as client:
            yield client

@pytest.fixture(scope="function")
def admin_token(client, db_session):
    """Fixture untuk membuat user admin dan login untuk mendapatkan token"""
    # Buat user admin
    hashed = hash_password("admin123")
    admin = User(username="admin", password_hash=hashed, role="admin")
    db_session.add(admin)
    db_session.commit()
    
    # Login
    response = client.post('/auth/login', json={
        "username": "admin",
        "password": "admin123"
    })
    return response.json['access_token']