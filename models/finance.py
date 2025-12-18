import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, DECIMAL, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base

# Enum untuk Kategori Akun
class AccountType(enum.Enum):
    ASSET = "ASSET"             # Harta (Kas, Bank, Inventaris)
    LIABILITY = "LIABILITY"     # Hutang
    EQUITY = "EQUITY"           # Modal/Saldo Awal
    REVENUE = "REVENUE"         # Pemasukan (Infaq, Wakaf)
    EXPENSE = "EXPENSE"         # Pengeluaran (Listrik, Kebersihan)

# Enum untuk Posisi Jurnal
class EntryType(enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True) # Contoh: 101, 401
    name: Mapped[str] = mapped_column(String(100)) # Contoh: Kas Masjid, Infaq Jumat
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relasi ke jurnal
    entries: Mapped[List["TransactionEntry"]] = relationship(back_populates="account")

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    description: Mapped[str] = mapped_column(String(255)) # Keterangan transaksi
    reference_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # No Bukti/Kwitansi
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relasi: Satu transaksi punya banyak baris jurnal (Debit & Kredit)
    entries: Mapped[List["TransactionEntry"]] = relationship(
        back_populates="transaction", 
        cascade="all, delete-orphan"
    )

class TransactionEntry(Base):
    __tablename__ = "transaction_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    
    entry_type: Mapped[EntryType] = mapped_column(Enum(EntryType)) # Debit / Kredit
    amount: Mapped[float] = mapped_column(DECIMAL(15, 2)) # Nominal uang
    
    transaction: Mapped["Transaction"] = relationship(back_populates="entries")
    account: Mapped["Account"] = relationship(back_populates="entries")