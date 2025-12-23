from flask import Flask, jsonify, request
from flasgger import Swagger
from core.database import SessionLocal, engine, Base
from api import schemas, services
from models.user import User
from core.security import hash_password, verify_password, create_access_token, token_required
from pydantic import ValidationError

# Inisialisasi App
app = Flask(__name__)

# --- KONFIGURASI SWAGGER ---
app.config['SWAGGER'] = {
    'title': 'Masjid Finance API',
    'uiversion': 3
}

# Definisi Template agar support JWT Bearer Token
swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Masjid Finance API",
        "description": "API Pencatatan Keuangan Masjid (Double Entry Bookkeeping)",
        "version": "1.0.0"
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Masukkan token dengan format: Bearer <your_token>"
        }
    }
}

swagger = Swagger(app, template=swagger_template)

# Middleware untuk DB Session
@app.teardown_appcontext
def shutdown_session(exception=None):
    """Menutup koneksi database setiap request selesai"""
    # Catatan: SessionLocal harus dikelola manual atau pakai Flask-SQLAlchemy
    # Di sini kita pakai cara manual sederhana
    pass 

def get_db():
    """Helper manual untuk route"""
    return SessionLocal()

# --- ROUTES AKUN (COA) ---

@app.route('/accounts', methods=['GET'])
def list_accounts():
    db = get_db()
    try:
        accounts = services.get_all_accounts(db)
        # Konversi object SQLAlchemy -> Pydantic -> Dict
        return jsonify([schemas.AccountResponse.model_validate(a).model_dump() for a in accounts])
    finally:
        db.close()

# --- FUNGSI BANTUAN SEED ADMIN ---
def create_default_admin():
    db = SessionLocal()
    try:
        # Cek apakah user admin sudah ada
        user = db.query(User).filter_by(username="admin").first()
        if not user:
            print("Membuat user default: admin / admin123")
            hashed = hash_password("admin123")
            new_admin = User(username="admin", password_hash=hashed, role="admin")
            db.add(new_admin)
            db.commit()
    finally:
        db.close()

# --- ROUTE AUTH (LOGIN) ---
@app.route('/auth/login', methods=['POST'])
def login():
    """
    Login User Admin
    Dapatkan Access Token untuk melakukan operasi tulis (POST).
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              example: admin
            password:
              type: string
              example: admin123
    responses:
      200:
        description: Login Berhasil
        schema:
          type: object
          properties:
            access_token:
              type: string
            token_type:
              type: string
      401:
        description: Password Salah
    """
    db = get_db()
    try:
        data = request.json
        # Cari user di DB
        user = db.query(User).filter_by(username=data.get('username')).first()
        
        # Validasi Password
        if not user or not verify_password(data.get('password'), user.password_hash):
            return jsonify({"message": "Username atau Password salah"}), 401
        
        # Buat Token
        token = create_access_token({"sub": user.username, "role": user.role})
        
        return jsonify({
            "access_token": token,
            "token_type": "bearer",
            "message": "Login berhasil"
        })
    finally:
        db.close()

@app.route('/accounts', methods=['POST'])
@token_required
def add_account():
    db = get_db()
    try:
        # 1. Validasi JSON masuk
        payload = schemas.AccountCreate(**request.json)
        # 2. Simpan ke DB
        new_acc = services.create_account(db, payload)
        # 3. Return response
        return jsonify(schemas.AccountResponse.model_validate(new_acc).model_dump()), 201
    except ValidationError as e:
        return jsonify(e.errors()), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

# --- ROUTES TRANSAKSI ---

@app.route('/transactions', methods=['POST'])
@token_required
def add_transaction():
    """
    Tambah Transaksi Baru (Jurnal Umum)
    Hanya bisa diakses oleh Admin yang memiliki Token.
    ---
    tags:
      - Transactions
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - description
            - entries
          properties:
            description:
              type: string
              example: "Membayar Listrik Bulan Ini"
            reference_no:
              type: string
              example: "PLN-OCT-23"
            entries:
              type: array
              items:
                type: object
                properties:
                  account_id:
                    type: integer
                    example: 5
                  entry_type:
                    type: string
                    enum: ['DEBIT', 'CREDIT']
                  amount:
                    type: number
                    example: 150000
    responses:
      201:
        description: Transaksi Berhasil Disimpan
      400:
        description: Validasi Gagal / Tidak Balance
      401:
        description: Unauthorized / Token Hilang
    """
    db = get_db()
    try:
        # Validasi Input (termasuk cek Balance Debit == Kredit)
        payload = schemas.TransactionCreate(**request.json)
        
        # Simpan
        new_tx = services.create_transaction(db, payload)
        
        return jsonify(schemas.TransactionResponse.model_validate(new_tx).model_dump()), 201
    except ValidationError as e:
        return jsonify({"message": "Validasi Gagal", "details": e.errors()}), 400
    except ValueError as e:
        # Error logic bisnis (misal tidak balance)
        return jsonify({"message": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/transactions', methods=['GET'])
def list_transactions():
    db = get_db()
    try:
        txs = services.get_transactions(db)
        return jsonify([schemas.TransactionResponse.model_validate(t).model_dump() for t in txs])
    finally:
        db.close()

# --- ROUTES LAPORAN ---

@app.route('/reports/balance-sheet', methods=['GET'])
def get_balance_sheet():
    """
    Lihat Laporan Neraca (Posisi Keuangan)
    Menampilkan Aset, Kewajiban, dan Modal (termasuk surplus/defisit berjalan).
    ---
    tags:
      - Reports
    responses:
      200:
        description: Laporan berhasil diambil
        schema:
          type: object
          properties:
            report_date:
              type: string
            assets:
              type: array
              items:
                type: object
            total_assets:
              type: number
            is_balance:
              type: boolean
    """
    db = get_db()
    try:
        report_data = services.generate_balance_sheet(db)
        # Validasi dengan Schema Pydantic sebelum return JSON
        return jsonify(schemas.BalanceSheetResponse(**report_data).model_dump())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@app.route('/reports/ledger/<int:account_id>', methods=['GET'])
def view_ledger(account_id):
    db = get_db()
    
    # Ambil parameter tanggal dari URL (opsional)
    start_date = request.args.get('start_date') # Format YYYY-MM-DD
    end_date = request.args.get('end_date')     # Format YYYY-MM-DD
    
    try:
        data = services.get_general_ledger(db, account_id, start_date, end_date)
        return jsonify(schemas.LedgerResponse(**data).model_dump())
    except ValueError as e:
        return jsonify({"message": str(e)}), 404
    except Exception as e:
        # Print error log di terminal untuk debugging
        print(e) 
        return jsonify({"error": "Terjadi kesalahan internal"}), 500
    finally:
        db.close()

if __name__ == '__main__':
    # Pastikan tabel dibuat jika belum ada (alternatif alembic untuk dev)
    # Base.metadata.create_all(bind=engine)
    create_default_admin()
    app.run(debug=True, port=5000)