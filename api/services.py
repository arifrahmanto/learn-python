from datetime import datetime
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from models.finance import Account, AccountType, EntryType, Transaction, TransactionEntry
from api.schemas import AccountCreate, TransactionCreate

def get_all_accounts(db: Session):
    return db.query(Account).order_by(Account.code).all()

def create_account(db: Session, account: AccountCreate):
    db_account = Account(
        code=account.code,
        name=account.name,
        account_type=account.account_type, # Konversi otomatis dari Enum Pydantic
        description=account.description
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

def create_transaction(db: Session, tx_data: TransactionCreate):
    # 1. Buat Header Transaksi
    new_tx = Transaction(
        description=tx_data.description,
        reference_no=tx_data.reference_no
    )
    
    # 2. Buat Detail Jurnal
    for entry in tx_data.entries:
        new_entry = TransactionEntry(
            account_id=entry.account_id,
            entry_type=entry.entry_type, # Konversi str ke Enum SQLAlchemy
            amount=entry.amount
        )
        # Append ke relasi (SQLAlchemy mengurus foreign key transaction_id)
        new_tx.entries.append(new_entry)
    
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)
    return new_tx

def get_transactions(db: Session, limit: int = 100):
    return db.query(Transaction).order_by(Transaction.transaction_date.desc()).limit(limit).all()

def calculate_balance(db: Session, account_id: int, account_type: AccountType) -> float:
    """Helper internal untuk menghitung saldo satu akun"""
    totals = db.query(
        func.sum(case((TransactionEntry.entry_type == EntryType.DEBIT, TransactionEntry.amount), else_=0)),
        func.sum(case((TransactionEntry.entry_type == EntryType.CREDIT, TransactionEntry.amount), else_=0))
    ).filter(TransactionEntry.account_id == account_id).first()
    
    debit, credit = totals if totals else (0, 0)
    debit = debit or 0
    credit = credit or 0

    # Rumus Saldo Normal:
    # Asset & Expense bertambah di Debit
    if account_type in [AccountType.ASSET, AccountType.EXPENSE]:
        return float(debit - credit)
    # Liability, Equity, Revenue bertambah di Kredit
    else:
        return float(credit - debit)

def generate_balance_sheet(db: Session):
    # 1. Hitung ASSETS
    asset_accounts = db.query(Account).filter(Account.account_type == AccountType.ASSET).all()
    assets_list = []
    total_assets = 0
    for acc in asset_accounts:
        bal = calculate_balance(db, acc.id, acc.account_type)
        if bal != 0:
            assets_list.append({"account_name": acc.name, "amount": bal})
            total_assets += bal

    # 2. Hitung LIABILITIES
    liab_accounts = db.query(Account).filter(Account.account_type == AccountType.LIABILITY).all()
    liab_list = []
    total_liabilities = 0
    for acc in liab_accounts:
        bal = calculate_balance(db, acc.id, acc.account_type)
        if bal != 0:
            liab_list.append({"account_name": acc.name, "amount": bal})
            total_liabilities += bal

    # 3. Hitung EQUITY (Modal Awal)
    equity_accounts = db.query(Account).filter(Account.account_type == AccountType.EQUITY).all()
    equity_list = []
    total_base_equity = 0
    for acc in equity_accounts:
        bal = calculate_balance(db, acc.id, acc.account_type)
        equity_list.append({"account_name": acc.name, "amount": bal})
        total_base_equity += bal

    # 4. Hitung SURPLUS/DEFISIT BERJALAN (Revenue - Expense)
    # Ini penting agar Balance Sheet seimbang
    rev_accounts = db.query(Account).filter(Account.account_type == AccountType.REVENUE).all()
    exp_accounts = db.query(Account).filter(Account.account_type == AccountType.EXPENSE).all()
    
    total_revenue = sum([calculate_balance(db, a.id, a.account_type) for a in rev_accounts])
    total_expense = sum([calculate_balance(db, a.id, a.account_type) for a in exp_accounts])
    
    current_earnings = total_revenue - total_expense
    
    # Masukkan Laba Rugi Berjalan ke List Ekuitas
    equity_list.append({
        "account_name": "Surplus/Defisit Berjalan (Laba Rugi)",
        "amount": current_earnings
    })
    
    total_equities = total_base_equity + current_earnings

    # 5. Cek Balance (Asset = Liability + Equity)
    # Gunakan toleransi kecil untuk floating point
    diff = total_assets - (total_liabilities + total_equities)
    is_balance = abs(diff) < 0.01

    return {
        "report_date": datetime.now().isoformat(),
        "assets": assets_list,
        "total_assets": total_assets,
        "liabilities": liab_list,
        "total_liabilities": total_liabilities,
        "equities": equity_list,
        "total_equities": total_equities,
        "is_balance": is_balance,
        "diff": diff
    }

def get_general_ledger(db: Session, account_id: int, start_date: str = None, end_date: str = None):
    # 1. Ambil Info Akun
    account = db.get(Account, account_id)
    if not account:
        raise ValueError("Akun tidak ditemukan")

    # Konversi string date ke object datetime (jika ada)
    # Asumsi format input "YYYY-MM-DD"
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    # Tentukan faktor pengali berdasarkan tipe akun
    # Asset/Expense: Debit menambah (+), Kredit mengurangi (-)
    # Liability/Equity/Revenue: Kredit menambah (+), Debit mengurangi (-)
    is_normal_debit = account.account_type in [AccountType.ASSET, AccountType.EXPENSE]

    # 2. Hitung OPENING BALANCE (Saldo Awal)
    # Yaitu total semua transaksi SEBELUM start_date
    opening_balance = 0.0
    
    if start_dt:
        # Query transaksi sebelum tanggal mulai
        hist_query = db.query(TransactionEntry).join(Transaction).filter(
            TransactionEntry.account_id == account_id,
            Transaction.transaction_date < start_dt
        )
        
        # Hitung manual (atau pakai func.sum sql)
        for entry in hist_query.all():
            amount = float(entry.amount)
            if entry.entry_type == EntryType.DEBIT:
                opening_balance += amount if is_normal_debit else -amount
            else: # CREDIT
                opening_balance -= amount if is_normal_debit else +amount

    # 3. Ambil Transaksi PERIODE BERJALAN
    query = db.query(TransactionEntry).join(Transaction).filter(
        TransactionEntry.account_id == account_id
    )

    if start_dt:
        query = query.filter(Transaction.transaction_date >= start_dt)
    if end_dt:
        # Set ke akhir hari (23:59:59) agar transaksi hari itu masuk semua
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        query = query.filter(Transaction.transaction_date <= end_dt)

    # Urutkan berdasarkan tanggal
    entries_db = query.order_by(Transaction.transaction_date.asc(), Transaction.id.asc()).all()

    # 4. Susun Data & Hitung Running Balance
    ledger_entries = []
    current_balance = opening_balance

    for entry in entries_db:
        amount = float(entry.amount)
        debit_amt = amount if entry.entry_type == EntryType.DEBIT else 0
        credit_amt = amount if entry.entry_type == EntryType.CREDIT else 0

        # Update Saldo Berjalan
        if is_normal_debit:
            current_balance += (debit_amt - credit_amt)
        else:
            current_balance += (credit_amt - debit_amt)

        ledger_entries.append({
            "transaction_date": entry.transaction.transaction_date,
            "description": entry.transaction.description,
            "reference_no": entry.transaction.reference_no,
            "debit": debit_amt,
            "credit": credit_amt,
            "balance": current_balance
        })

    return {
        "account_id": account.id,
        "account_name": account.name,
        "account_code": account.code,
        "period_start": start_date,
        "period_end": end_date,
        "opening_balance": opening_balance,
        "closing_balance": current_balance,
        "entries": ledger_entries
    }