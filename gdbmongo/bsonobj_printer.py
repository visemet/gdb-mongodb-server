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

import gdb

from gdbmongo.string_data_printer import MongoStringData


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
