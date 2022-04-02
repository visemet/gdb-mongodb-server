###
# Copyright 2022-present MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###
"""Pretty-printers for BSON-related data types."""

import ctypes
import dataclasses
import struct
import typing

import gdb

from gdbmongo.bsonmisc_printer import (MongoBSONBinData, MongoBSONCode, MongoBSONDBRef,
                                       MongoBSONRegEx, MongoBSONSymbol)
from gdbmongo.date_printer import MongoDateT
from gdbmongo.lock_manager_printer import gdb_lookup_value
from gdbmongo.objectid_printer import MongoOID
from gdbmongo.string_data_printer import MongoStringData
from gdbmongo.timestamp_printer import MongoTimestamp


@dataclasses.dataclass
class MongoBSONObj(ctypes.Structure):
    # pylint: disable=missing-function-docstring
    """Structure with a memory layout compatible with that of mongo::BSONObj.

    This class is useful for constructing gdb.Value objects of type mongo::BSONObj out of selected
    portions of a buffer read with gdb.Inferior.read_memory(). These synthetic gdb.Values can then
    be formatted by BSONObjPrinter like normal.

    .. code-block:: python

        bsonobj = MongoBSONObj(objdata=int(self.val["_objdata"]))
        yield (f"{i}", bsonobj.to_value())
    """

    objdata: ctypes.c_char_p
    _owned_buffer: ctypes.c_void_p

    def __init__(self, *, objdata: int) -> None:
        super().__init__(objdata=ctypes.c_char_p(objdata), _owned_buffer=ctypes.c_void_p(0))

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::BSONObj."""
        typ = gdb.lookup_type("mongo::BSONObj")
        return gdb.Value(memoryview(self), typ)


setattr(MongoBSONObj, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoBSONObj)])


# pylint: disable-next=too-few-public-methods
class MongoBSONArray(MongoBSONObj):
    """Structure with a memory layout compatible with that of mongo::BSONArray.

    This class is useful for constructing gdb.Value objects of type mongo::BSONArray out of selected
    portions of a buffer read with gdb.Inferior.read_memory(). These synthetic gdb.Values can then
    be formatted by BSONArrayPrinter like normal.

    .. code-block:: python

        bsonarray = MongoBSONArray(objdata=int(self.val["_objdata"]))
        yield (f"{i}", bsonarray.to_value())
    """

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::BSONArray."""
        typ = gdb.lookup_type("mongo::BSONArray")
        # Attempting to write this line as `return super().to_value().cast(typ)` leads to a
        # "Cannot access memory at address 0x0" error within GDB.
        return gdb.Value(memoryview(self), typ)


@dataclasses.dataclass
class MongoBSONCodeWScope(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::BSONCodeWScope.

    This class is useful for constructing gdb.Value objects of type mongo::BSONCodeWScope out of
    selected portions of a buffer read with gdb.Inferior.read_memory().
    """

    code: MongoStringData
    scope: MongoBSONObj

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::BSONCodeWScope."""
        typ = gdb.lookup_type("mongo::BSONCodeWScope")
        return gdb.Value(memoryview(self), typ)


setattr(MongoBSONCodeWScope, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoBSONCodeWScope)])


@dataclasses.dataclass
class MongoDecimal128(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::Decimal128.

    This class is useful for constructing gdb.Value objects of type mongo::Decimal128 out of
    selected portions of a buffer read with gdb.Inferior.read_memory().

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        decimal_data = MongoTimestamp.unpack_from(objdata)
        yield (f"{i}", decimal_data.to_value())
    """

    low64: ctypes.c_uint64
    high64: ctypes.c_uint64

    @classmethod
    def unpack_from(cls, buffer: memoryview, /) -> "MongoDecimal128":
        """Read a 16-byte Decimal128 value starting from the beginning of the given buffer."""
        fmt = "<QQ"
        (low, high) = struct.unpack_from(fmt, buffer)
        return cls(low64=ctypes.c_uint64(low), high64=ctypes.c_uint64(high))

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::Decimal128."""
        typ = gdb.lookup_type("mongo::Decimal128")
        return gdb.Value(memoryview(self), typ)


setattr(MongoDecimal128, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoDecimal128)])


def invalid_bson(_val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Return a gdb.Value representing invalid BSON was read from the given buffer."""
    return (gdb.Value("Invalid BSON"), len(view))


def unpack_cstring(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a null-terminated string starting from the beginning of the given buffer."""
    string_data = MongoStringData.from_cstring(val, maxsize=len(view))
    return (string_data.to_value(), string_data.size.value + 1)


def unpack_double(_val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read an 8-byte floating-point value starting from the beginning of the given buffer."""
    fmt = "<d"
    (ret, ) = struct.unpack_from(fmt, view)
    return (gdb.Value(ret), struct.calcsize(fmt))


def unpack_string(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a length-prefixed string starting from the beginning of the given buffer."""
    string_data = MongoStringData.from_pascalstring(val, view=view)
    return (string_data.to_value(), string_data.size.value + 4)


def unpack_object(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a BSONObj starting from the beginning of the given buffer."""
    (objsize, ) = struct.unpack_from("<i", view)
    return (MongoBSONObj(objdata=int(val)).to_value(), objsize)


def unpack_array(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a BSONArray starting from the beginning of the given buffer."""
    (objsize, ) = struct.unpack_from("<i", view)
    return (MongoBSONArray(objdata=int(val)).to_value(), objsize)


def unpack_binary(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a length-prefixed blob of binary data starting from the beginning of the given
    buffer.
    """
    binary_data = MongoBSONBinData.unpack_from(val, view=view)
    return (binary_data.to_value(), binary_data.length.value + 5)


def unpack_undefined(_val: gdb.Value, _view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Return a gdb.Value representing a literal undefined value."""
    ret = gdb_lookup_value("mongo::BSONUndefined")
    assert ret is not None
    return (ret, 0)


def unpack_object_id(_val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a 12-byte ObjectId starting from the beginning of the given buffer."""
    object_id = MongoOID.unpack_from(view)
    return (object_id.to_value(), 12)


def unpack_bool(_val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a 1-byte boolean value starting from the beginning of the given buffer."""
    fmt = "<b"
    (ret, ) = struct.unpack_from(fmt, view)
    return (gdb.Value(bool(ret)), struct.calcsize(fmt))


def unpack_date(_val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read an 8-byte date starting from the beginning of the given buffer."""
    date_t = MongoDateT.unpack_from(view)
    return (date_t.to_value(), 8)


def unpack_null(_val: gdb.Value, _view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Return a gdb.Value representing a literal null value."""
    ret = gdb_lookup_value("mongo::BSONNULL")
    assert ret is not None
    return (ret, 0)


def unpack_regexp(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read two null-terminated strings starting from the beginning of the given buffer."""
    regexp = MongoBSONRegEx.unpack_from(val, view=view)
    return (regexp.to_value(), regexp.pattern.size.value + regexp.flags.size.value + 2)


def unpack_db_pointer(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a length-prefixed string and a 12-byte ObjectId starting from the beginning of the given
    buffer.
    """
    db_pointer = MongoBSONDBRef.unpack_from(val, view=view)
    return (db_pointer.to_value(), db_pointer.namespace.size.value + 16)


def unpack_javascript(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a length-prefixed string from the beginning of the given buffer."""
    javascript = MongoBSONCode.unpack_from(val, view=view)
    return (javascript.to_value(), javascript.code.size.value + 4)


def unpack_symbol(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a length-prefixed string from the beginning of the given buffer."""
    symbol = MongoBSONSymbol.unpack_from(val, view=view)
    return (symbol.to_value(), symbol.symbol.size.value + 4)


def unpack_code_with_scope(val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a length-prefixed blob of a length-prefixed string and a BSONObj from the beginning of
    the given buffer.
    """
    fmt = "<i"
    (total_size, ) = struct.unpack_from(fmt, view)
    offset = struct.calcsize(fmt)
    code = MongoStringData.from_pascalstring(val + offset, view=view[offset:])
    scope = MongoBSONObj(objdata=int(val + offset + code.size.value + 4))
    return (MongoBSONCodeWScope(code=code, scope=scope).to_value(), total_size)


def unpack_int32(_val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a 4-byte integer value starting from the beginning of the given buffer."""
    fmt = "<i"
    (ret, ) = struct.unpack_from(fmt, view)
    return (gdb.Value(ret), struct.calcsize(fmt))


def unpack_timestamp(_val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read an 8-byte Timestamp starting from the beginning of the given buffer."""
    timestamp = MongoTimestamp.unpack_from(view)
    return (timestamp.to_value(), 8)


def unpack_int64(_val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read an 8-byte integer value starting from the beginning of the given buffer."""
    fmt = "<q"
    (ret, ) = struct.unpack_from(fmt, view)
    return (gdb.Value(ret), struct.calcsize(fmt))


def unpack_decimal128(_val: gdb.Value, view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Read a 16-byte Decimal128 value starting from the beginning of the given buffer."""
    decimal_data = MongoDecimal128.unpack_from(view)
    return (decimal_data.to_value(), 16)


def unpack_minkey(_val: gdb.Value, _view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Return a gdb.Value representing a literal MinKey value."""
    ret = gdb_lookup_value("mongo::MINKEY")
    assert ret is not None
    return (ret, 0)


def unpack_maxkey(_val: gdb.Value, _view: memoryview, /) -> typing.Tuple[gdb.Value, int]:
    """Return a gdb.Value representing a literal MaxKey value."""
    ret = gdb_lookup_value("mongo::MAXKEY")
    assert ret is not None
    return (ret, 0)
