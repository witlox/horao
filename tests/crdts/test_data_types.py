import struct

import packify

from horao.crdts.data_types import (
    Bytes,
    ComplexType,
    Float,
    Integer,
    Nothing,
    ReplicatedGrowableArrayItem,
    String,
)
from horao.crdts.protocols import Data


def test_str_implements_data_protocol():
    assert isinstance(String(""), Data)


def test_str_value_is_str_type():
    dw = String("test")
    assert type(dw.value) is str


def test_str_pack_returns_bytes():
    dw = String("test")
    assert type(dw.pack()) is bytes


def test_str_unpack_returns_instance():
    data = struct.pack("!4s", bytes("test", "utf-8"))
    unpacked = String.unpack(data)
    assert type(unpacked) is String


def test_str_pack_unpack_e2e():
    dw = String("test")
    packed = dw.pack()
    unpacked = String.unpack(packed)
    assert dw == unpacked


# BytesWrapper tests
def test_bytes_implements_data_protocol():
    assert isinstance(Bytes(b""), Data)


def test_bytes_value_is_bytes_type():
    dw = Bytes(b"test")
    assert type(dw.value) is bytes


def test_bytes_pack_returns_bytes():
    dw = Bytes(b"test")
    assert type(dw.pack()) is bytes


def test_bytes_unpack_returns_instance():
    data = struct.pack("!4s", b"test")
    unpacked = Bytes.unpack(data)
    assert type(unpacked) is Bytes


def test_bytes_pack_unpack_e2e():
    dw = Bytes(b"test")
    packed = dw.pack()
    unpacked = Bytes.unpack(packed)
    assert dw == unpacked


# DecimalWrapper tests
def test_float_implements_data_protocol():
    assert isinstance(Float(0), Data)


def test_float_pack_unpack_e2e():
    dw = Float(0)
    packed = dw.pack()
    unpacked = Float.unpack(packed)
    assert dw == unpacked


def test_float_comparisons():
    dw0 = Float(0)
    dw1 = Float(1)

    assert dw0 == dw0
    assert dw1 > dw0
    assert dw1 >= dw0
    assert dw0 < dw1
    assert dw0 <= dw1


# IntWrapper tests
def test_int_implements_data_protocol():
    assert isinstance(Integer(1), Data)


def test_int_value_is_int_type():
    dw = Integer(1)
    assert type(dw.value) is int


def test_int_pack_returns_bytes():
    dw = Integer(1)
    assert type(dw.pack()) is bytes


def test_int_unpack_returns_instance():
    data = struct.pack("!i", 123)
    unpacked = Integer.unpack(data)
    assert type(unpacked) is Integer


def test_int_pack_unpack_e2e():
    dw = Integer(321)
    packed = dw.pack()
    unpacked = Integer.unpack(packed)
    assert dw == unpacked


def test_int_comparisons():
    dw0 = Integer(123)
    dw1 = Integer(321)

    assert dw0 == dw0
    assert dw1 > dw0
    assert dw1 >= dw0
    assert dw0 < dw1
    assert dw0 <= dw1


# RGAItemWrapper tests
def test_rga_item_implements_data_protocol():
    rgatw = ReplicatedGrowableArrayItem(Bytes(b"123"), Integer(1), 1)
    assert isinstance(rgatw, Data)


def test_rga_item_values_are_correct_types():
    rgatw = ReplicatedGrowableArrayItem(Bytes(b"123"), Integer(1), 1)
    assert isinstance(rgatw.value, Data)
    assert isinstance(rgatw.time_stamp, Data)
    assert type(rgatw.writer) is int


def test_rga_item_raises_usage_error_for_bad_value():
    try:
        ReplicatedGrowableArrayItem(
            Bytes(b"123"),
            Bytes(b"321"),
            lambda: "not a packify.SerializableType",
        )
    except TypeError as e:
        assert str(e.exception) == "writer must be SerializableType"


def test_rga_item_pack_returns_bytes():
    rgatw = ReplicatedGrowableArrayItem(Bytes(b"123"), Integer(1), 1)
    packed = rgatw.pack()
    assert type(packed) is bytes


def test_rga_item_pack_unpack_e2e():
    rgatw = ReplicatedGrowableArrayItem(Bytes(b"123"), Bytes(b"adfsf"), 1)
    packed = rgatw.pack()
    unpacked = ReplicatedGrowableArrayItem.unpack(packed)
    assert rgatw == unpacked


# CTDataWrapper
def test_cdt_data_implements_data_protocol():
    ctw = ComplexType(Bytes(b"123"), b"321", b"123")
    assert isinstance(ctw, Data)


def test_cdt_data_properties_are_correct_types():
    ctw = ComplexType(Bytes(b"123"), b"321", b"123")
    assert isinstance(ctw.value, Data)
    assert type(ctw.uuid) is bytes
    assert type(ctw.parent_uuid) is bytes


def test_cdt_data_raises_usage_error_for_bad_value():
    try:
        ComplexType(Bytes(b"123"), "321", b"123")
    except TypeError as e:
        assert str(e.exception) == "uuid must be bytes"

    try:
        ComplexType(Bytes(b"123"), b"123", 123)
    except TypeError as e:
        assert str(e.exception) == "parent_uuid must be bytes"

    try:
        ComplexType(Bytes(b"1"), b"1", b"1", "f")
    except TypeError as e:
        assert str(e.exception) == "visible must be bool"


def test_cdt_data_pack_returns_bytes():
    ctw = ComplexType(Bytes(b"123"), b"321", b"123")
    packed = ctw.pack()
    assert type(packed) is bytes


def test_cdt_data_pack_unpack_e2e():
    ctw = ComplexType(Bytes(b"123"), b"321", b"123")
    packed = ctw.pack()
    unpacked = ComplexType.unpack(packed)
    assert ctw == unpacked


def test_cdt_data_comparisons():
    ctw1 = ComplexType(Bytes(b"123"), b"321", b"123")
    ctw2 = ComplexType(Bytes(b"123"), b"321", b"123", False)
    assert ctw1 != ctw2
    assert hash(ctw1) != hash(ctw2)


def test_none_implements_data_protocol():
    assert isinstance(Nothing, Data)
