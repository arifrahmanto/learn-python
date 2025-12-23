def test_login_success(client, db_session):
    # Buat user manual di DB
    from models.user import User
    from core.security import hash_password
    
    pwd = hash_password("pass123")
    user = User(username="testadmin", password_hash=pwd, role="admin")
    db_session.add(user)
    db_session.commit()
    
    resp = client.post('/auth/login', json={"username": "testadmin", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json
    assert resp.json["token_type"] == "bearer"

def test_login_failed(client):
    resp = client.post('/auth/login', json={"username": "ngawur", "password": "salah"})
    assert resp.status_code == 401

def test_create_account_endpoint(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "code": "1005",
        "name": "Bank Syariah",
        "account_type": "ASSET",
        "description": "Rekening Bank"
    }
    resp = client.post('/accounts', json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json['code'] == "1005"

def test_create_account_unauthorized(client):
    # Tanpa Token
    payload = {
        "code": "1006",
        "name": "Bank Gelap",
        "account_type": "ASSET"
    }
    resp = client.post('/accounts', json=payload)
    assert resp.status_code == 401

def test_create_transaction_endpoint(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Perlu buat akun dulu agar ID valid
    client.post('/accounts', json={"code":"1","name":"A","account_type":"ASSET"}, headers=headers)
    client.post('/accounts', json={"code":"2","name":"B","account_type":"LIABILITY"}, headers=headers)
    
    # Ambil ID akun (asumsi ID 1 dan 2 karena DB reset per function)
    payload = {
        "description": "Bayar Hutang",
        "entries": [
            {"account_id": 1, "entry_type": "CREDIT", "amount": 50000},
            {"account_id": 2, "entry_type": "DEBIT", "amount": 50000}
        ]
    }
    resp = client.post('/transactions', json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json['description'] == "Bayar Hutang"

def test_get_balance_sheet_endpoint(client):
    resp = client.get('/reports/balance-sheet')
    assert resp.status_code == 200
    assert "total_assets" in resp.json