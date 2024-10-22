from dataclasses import is_dataclass
from decimal import Decimal

from horao.crdts import Update
from horao.crdts.clock import ScalarClock
from horao.crdts.data_types import (
    Bytes,
    ComplexType,
    Float,
    FractionallyIndexedArrayItem,
    Integer,
    Nothing,
    ReplicatedGrowableArrayItem,
    String,
)

inject = {
    "Bytes": Bytes,
    "String": String,
    "Integer": Integer,
    "Float": Float,
    "ComplexType": ComplexType,
    "ReplicatedGrowableArrayItem": ReplicatedGrowableArrayItem,
    "FractionallyIndexedArrayItem": FractionallyIndexedArrayItem,
    "Nothing": Nothing,
    "ScalarClock": ScalarClock,
}


def test_state_is_dataclass_with_attributes():
    update = Update(b"123", 123, 321)
    assert is_dataclass(update)
    assert isinstance(update, Update)


def test_state_pack_returns_bytes():
    update = Update(b"123", 123, 321)
    assert type(update.pack()) is bytes


def test_state_unpack_returns_state_update():
    data = bytes.fromhex(
        "6c0000001a620000000331323369000000040000007b690000000400000141"
    )
    update = Update.unpack(data)
    assert isinstance(update, Update)


def test_state_pack_unpack_e2e():
    update = Update(b"uuid", 123, ("o", (321, "123")))
    packed = update.pack()
    unpacked = Update.unpack(packed)
    assert unpacked == update

    update = Update(b"uuid", 123, (1, Bytes(b"example")))
    packed = update.pack()
    unpacked = Update.unpack(packed, inject=inject)
    assert unpacked == update

    update = Update(b"uuid", 123, ("o", String("name"), 1, Bytes(b"value")))
    packed = update.pack()
    unpacked = Update.unpack(packed, inject=inject)
    assert unpacked == update

    update = Update(b"uuid", 123, ("o", Integer(3), 1, Float(0.253)))
    packed = update.pack()
    unpacked = Update.unpack(packed, inject=inject)
    assert unpacked == update
