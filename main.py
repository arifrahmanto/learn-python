from sqlalchemy import func
from core.database import SessionLocal
from models.finance import Account, AccountType, Transaction, TransactionEntry, EntryType

def init_coa(db):
    """Membuat Chart of Accounts (COA) dasar jika belum ada"""
    if db.query(Account).count() > 0:
        return

    coa_list = [
        # Harta
        Account(code="1001", name="Kas Takmir", account_type=AccountType.ASSET),
        Account(code="1002", name="Kas Pembangunan", account_type=AccountType.ASSET),
        # Pemasukan
        Account(code="4001", name="Infaq Kotak Jumat", account_type=AccountType.REVENUE),
        Account(code="4002", name="Infaq Pembangunan", account_type=AccountType.REVENUE),
        # Pengeluaran
        Account(code="5001", name="Biaya Listrik", account_type=AccountType.EXPENSE),
        Account(code="5002", name="Honor Muadzin", account_type=AccountType.EXPENSE),
    ]
    db.add_all(coa_list)
    db.commit()
    print("Chart of Accounts berhasil dibuat.")

def catat_pemasukan_infaq(db, jumlah: float, keterangan: str):
    """
    Mencatat Pemasukan Infaq Jumat.
    Debit: Kas Tunai
    Kredit: Pendapatan Infaq
    """
    # Cari Akun
    akun_kas = db.query(Account).filter_by(code="1001").first()
    akun_pendapatan = db.query(Account).filter_by(code="4001").first()

    # Buat Transaksi Header
    transaksi = Transaction(description=keterangan)

    # Buat Detail Jurnal (Double Entry)
    entry_debit = TransactionEntry(
        account=akun_kas, 
        entry_type=EntryType.DEBIT, 
        amount=jumlah
    )
    entry_credit = TransactionEntry(
        account=akun_pendapatan, 
        entry_type=EntryType.CREDIT, 
        amount=jumlah
    )

    # Assign entries ke transaksi
    transaksi.entries = [entry_debit, entry_credit]
    
    db.add(transaksi)
    db.commit()
    print(f"Transaksi Masuk: {keterangan} sebesar Rp {jumlah:,.2f}")

def laporan_saldo_kas(db):
    """Menghitung saldo Kas Tunai saat ini"""
    akun_kas = db.query(Account).filter_by(code="1001").first()
    
    # Hitung total Debit dan Kredit untuk akun ini
    total_debit = db.query(func.sum(TransactionEntry.amount))\
        .filter(TransactionEntry.account_id == akun_kas.id, TransactionEntry.entry_type == EntryType.DEBIT).scalar() or 0
    
    total_credit = db.query(func.sum(TransactionEntry.amount))\
        .filter(TransactionEntry.account_id == akun_kas.id, TransactionEntry.entry_type == EntryType.CREDIT).scalar() or 0
    
    # Saldo Asset = Debit - Kredit
    saldo = total_debit - total_credit
    print(f"--- SALDO {akun_kas.name} SAAT INI: Rp {saldo:,.2f} ---")

if __name__ == "__main__":
    db = SessionLocal()
    
    # 1. Setup Awal
    init_coa(db)
    
    # 2. Simulasi: Terima Infaq Jumat
    catat_pemasukan_infaq(db, 5000000, "Infaq Jumat Pekan 1 Desember")
    
    # 3. Simulasi: Bayar Listrik (Debit: Biaya Listrik, Kredit: Kas)
    # Anda bisa membuat fungsi `catat_pengeluaran` serupa dengan `catat_pemasukan_infaq`
    
    # 4. Cek Laporan
    laporan_saldo_kas(db)
    
    db.close()