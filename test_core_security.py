import jwt
from core.security import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM

def test_password_hashing():
    password = "mysecretpassword"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_jwt_token_creation():
    data = {"sub": "testuser", "role": "admin"}
    token = create_access_token(data)
    
    assert isinstance(token, str)
    
    # Decode manual untuk memastikan isi payload benar
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "testuser"
    assert decoded["role"] == "admin"
    assert "exp" in decoded