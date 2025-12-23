import pytest
from pydantic import ValidationError
from api.schemas import TransactionCreate, TransactionEntryCreate, EntryTypeEnum

def test_transaction_balance_validation():
    # Case 1: Balance (Debit 100, Credit 100) -> Harus Sukses
    entries = [
        TransactionEntryCreate(account_id=1, entry_type=EntryTypeEnum.DEBIT, amount=100),
        TransactionEntryCreate(account_id=2, entry_type=EntryTypeEnum.CREDIT, amount=100)
    ]
    tx = TransactionCreate(description="Test Balance", entries=entries)
    assert len(tx.entries) == 2

    # Case 2: Tidak Balance (Debit 100, Credit 50) -> Harus Error
    entries_unbalanced = [
        TransactionEntryCreate(account_id=1, entry_type=EntryTypeEnum.DEBIT, amount=100),
        TransactionEntryCreate(account_id=2, entry_type=EntryTypeEnum.CREDIT, amount=50)
    ]
    
    with pytest.raises(ValidationError) as excinfo:
        TransactionCreate(description="Test Unbalanced", entries=entries_unbalanced)
    
    # Pastikan pesan error sesuai dengan validator kita
    assert "Jurnal tidak balance" in str(excinfo.value)

def test_amount_must_be_positive():
    # Amount tidak boleh negatif atau 0
    with pytest.raises(ValidationError):
        TransactionEntryCreate(account_id=1, entry_type=EntryTypeEnum.DEBIT, amount=-50)
        
    with pytest.raises(ValidationError):
        TransactionEntryCreate(account_id=1, entry_type=EntryTypeEnum.DEBIT, amount=0)