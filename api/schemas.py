from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from enum import Enum

# Enum agar input JSON harus string spesifik
class EntryTypeEnum(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class AccountTypeEnum(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# --- SCHEMAS UNTUK AKUN ---
class AccountCreate(BaseModel):
    code: str
    name: str
    account_type: AccountTypeEnum
    description: Optional[str] = None

class AccountResponse(AccountCreate):
    id: int
    
    class Config:
        from_attributes = True

# --- SCHEMAS UNTUK TRANSAKSI ---
class TransactionEntryCreate(BaseModel):
    account_id: int
    entry_type: EntryTypeEnum
    amount: float = Field(..., gt=0, description="Nominal harus lebih dari 0")

class TransactionCreate(BaseModel):
    description: str
    reference_no: Optional[str] = None
    entries: List[TransactionEntryCreate]

    @validator('entries')
    def validate_balance(cls, v):
        """Validasi Double Entry: Total Debit harus sama dengan Total Kredit"""
        total_debit = sum(e.amount for e in v if e.entry_type == EntryTypeEnum.DEBIT)
        total_credit = sum(e.amount for e in v if e.entry_type == EntryTypeEnum.CREDIT)
        
        # Toleransi floating point kecil
        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(f'Jurnal tidak balance! Debit: {total_debit}, Kredit: {total_credit}')
        return v

class TransactionEntryResponse(TransactionEntryCreate):
    id: int
    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: int
    transaction_date: datetime
    description: str
    reference_no: Optional[str]
    entries: List[TransactionEntryResponse]

    class Config:
        from_attributes = True

# Schema untuk satu baris akun (misal: "Kas Masjid": 5.000.000)
class BalanceLineItem(BaseModel):
    account_name: str
    amount: float

# Schema untuk Struktur Lengkap Neraca
class BalanceSheetResponse(BaseModel):
    report_date: str
    
    # Bagian Aset
    assets: List[BalanceLineItem]
    total_assets: float
    
    # Bagian Kewajiban
    liabilities: List[BalanceLineItem]
    total_liabilities: float
    
    # Bagian Ekuitas (Modal)
    equities: List[BalanceLineItem]
    total_equities: float
    
    # Pengecekan Balance
    is_balance: bool
    diff: float  # Selisih (seharusnya 0)

# --- SCHEMAS UNTUK BUKU BESAR (LEDGER) ---

class LedgerEntryItem(BaseModel):
    transaction_date: datetime
    description: str
    reference_no: Optional[str]
    debit: float
    credit: float
    balance: float  # Saldo setelah transaksi ini

class LedgerResponse(BaseModel):
    account_id: int
    account_name: str
    account_code: str
    period_start: Optional[str]
    period_end: Optional[str]
    opening_balance: float      # Saldo sebelum periode yang dipilih
    closing_balance: float      # Saldo akhir periode
    entries: List[LedgerEntryItem]