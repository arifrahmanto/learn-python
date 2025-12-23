from api import services
from api.schemas import AccountCreate, AccountTypeEnum, TransactionCreate, TransactionEntryCreate, EntryTypeEnum
from models.finance import Account

def test_create_account(db_session):
    account_data = AccountCreate(
        code="1001",
        name="Kas Test",
        account_type=AccountTypeEnum.ASSET,
        description="Akun Kas untuk Testing"
    )
    new_acc = services.create_account(db_session, account_data)
    
    assert new_acc.id is not None
    assert new_acc.code == "1001"
    
    # Verifikasi tersimpan di DB
    db_acc = db_session.query(Account).filter_by(code="1001").first()
    assert db_acc is not None
    assert db_acc.name == "Kas Test"

def test_create_transaction_and_balance(db_session):
    # 1. Setup Akun
    acc_kas = services.create_account(db_session, AccountCreate(code="101", name="Kas", account_type=AccountTypeEnum.ASSET))
    acc_rev = services.create_account(db_session, AccountCreate(code="401", name="Pendapatan", account_type=AccountTypeEnum.REVENUE))
    
    # 2. Buat Transaksi (Terima Uang 50.000)
    entries = [
        TransactionEntryCreate(account_id=acc_kas.id, entry_type=EntryTypeEnum.DEBIT, amount=50000),
        TransactionEntryCreate(account_id=acc_rev.id, entry_type=EntryTypeEnum.CREDIT, amount=50000)
    ]
    tx_data = TransactionCreate(description="Terima Infaq", entries=entries)
    
    new_tx = services.create_transaction(db_session, tx_data)
    assert new_tx.id is not None
    
    # 3. Test Perhitungan Saldo (calculate_balance)
    # Asset (Debit) bertambah positif
    bal_kas = services.calculate_balance(db_session, acc_kas.id, acc_kas.account_type)
    assert bal_kas == 50000.0
    
    # Revenue (Kredit) bertambah positif (sesuai logic services: credit - debit)
    bal_rev = services.calculate_balance(db_session, acc_rev.id, acc_rev.account_type)
    assert bal_rev == 50000.0

def test_generate_balance_sheet(db_session):
    # Setup: Kas (Asset) 100, Modal (Equity) 100
    acc_kas = services.create_account(db_session, AccountCreate(code="101", name="Kas", account_type=AccountTypeEnum.ASSET))
    acc_modal = services.create_account(db_session, AccountCreate(code="301", name="Modal", account_type=AccountTypeEnum.EQUITY))
    
    entries = [
        TransactionEntryCreate(account_id=acc_kas.id, entry_type=EntryTypeEnum.DEBIT, amount=100),
        TransactionEntryCreate(account_id=acc_modal.id, entry_type=EntryTypeEnum.CREDIT, amount=100)
    ]
    services.create_transaction(db_session, TransactionCreate(description="Modal Awal", entries=entries))
    
    # Generate Report
    report = services.generate_balance_sheet(db_session)
    
    assert report['total_assets'] == 100.0
    assert report['total_equities'] == 100.0
    assert report['is_balance'] is True
    assert report['diff'] == 0.0

def test_get_general_ledger(db_session):
    acc = services.create_account(db_session, AccountCreate(code="101", name="Kas", account_type=AccountTypeEnum.ASSET))
    
    # Transaksi 1: Masuk 1000
    entries1 = [
        TransactionEntryCreate(account_id=acc.id, entry_type=EntryTypeEnum.DEBIT, amount=1000),
        TransactionEntryCreate(account_id=acc.id, entry_type=EntryTypeEnum.CREDIT, amount=1000) # Dummy credit ke diri sendiri biar balance utk test ini
    ]
    services.create_transaction(db_session, TransactionCreate(description="Tx1", entries=entries1))
    
    ledger = services.get_general_ledger(db_session, acc.id)
    
    assert ledger['account_code'] == "101"
    assert len(ledger['entries']) == 2
    # Cek running balance entri pertama (Debit 1000 -> Saldo 1000)
    assert ledger['entries'][0]['debit'] == 1000
    assert ledger['entries'][0]['balance'] == 1000