import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify

# Ganti dengan secret key yang sangat rahasia di production!
SECRET_KEY = "rahasia_illahi_masjid_berkah"
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    # Mengubah password text menjadi hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: int = 60):
    # Token berlaku selama 60 menit defaultnya
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- DECORATOR UTAMA ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Cek Header: Authorization: Bearer <token>
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1] # Ambil tokennya saja
        
        if not token:
            return jsonify({'message': 'Token tidak ditemukan! Harap login.'}), 401
        
        try:
            # Decode Token
            data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # (Opsional) Kita bisa cek apakah user masih aktif di DB, tapi ini cukup untuk stateless
            current_user = data['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token sudah kadaluarsa! Silakan login ulang.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token tidak valid!'}), 401
            
        return f(*args, **kwargs)
    
    return decorated