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
"""Pretty-printers for BSON-related utility classes received by mongo::BSONObjBuilder for appending
specific data types. These utility classes realistically won't appear as variables or members in
other C++ classes but are leveraged as gdb.Types which gdbmongo.bsonobj_printer.BSONObjPrinter can
represent those data types as.
"""

import ctypes
import dataclasses
import struct

import gdb

from gdbmongo.objectid_printer import MongoOID
from gdbmongo.printer_protocol import SupportsToString
from gdbmongo.string_data_printer import MongoStringData


# pylint: disable-next=invalid-name
# pylint: disable-next=too-few-public-methods
class c_int32(ctypes.c_int32):
    """Wrapper class for ctypes.c_int32 to avoid implicit conversion to int."""


# pylint: disable-next=invalid-name
# pylint: disable-next=too-few-public-methods
class c_void_p(ctypes.c_void_p):
    """Wrapper class for ctypes.c_void_p to avoid implicit conversion to int."""


@dataclasses.dataclass
class MongoBSONBinData(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::BSONBinData.

    This class is useful for constructing gdb.Value objects of type mongo::BSONBinData out of
    selected portions of a buffer read with gdb.Inferior.read_memory().

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        binary_data = MongoBSONBinData.unpack_from(self.val["_objdata"], view=objdata)
        yield (f"{i}", binary_data.to_value())
    """

    data: c_void_p
    length: c_int32
    type: c_int32

    @classmethod
    def unpack_from(cls, val: gdb.Value, /, *, view: memoryview) -> "MongoBSONBinData":
        """Read a length-prefixed blob of binary data starting from the beginning of the given
        buffer.
        """
        fmt = "<iB"
        (length, subtype) = struct.unpack_from(fmt, view)
        return cls(data=c_void_p(int(val)), length=c_int32(length), type=c_int32(subtype))

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::BSONBinData."""
        typ = gdb.lookup_type("mongo::BSONBinData")
        return gdb.Value(memoryview(self), typ)


setattr(MongoBSONBinData, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoBSONBinData)])


@dataclasses.dataclass
class MongoBSONCode(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::BSONCode.

    This class is useful for constructing gdb.Value objects of type mongo::BSONCode out of selected
    portions of a buffer read with gdb.Inferior.read_memory().

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        javascript = MongoBSONCode.unpack_from(self.val["_objdata"], view=objdata)
        yield (f"{i}", javascript.to_value())
    """

    code: MongoStringData

    @classmethod
    def unpack_from(cls, val: gdb.Value, /, *, view: memoryview) -> "MongoBSONCode":
        """Read a length-prefixed string from the beginning of the given buffer."""
        code = MongoStringData.from_pascalstring(val, view=view)
        return cls(code=code)

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::BSONCode."""
        typ = gdb.lookup_type("mongo::BSONCode")
        return gdb.Value(memoryview(self), typ)


setattr(MongoBSONCode, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoBSONCode)])


@dataclasses.dataclass
class MongoBSONDBRef(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::BSONDBRef.

    This class is useful for constructing gdb.Value objects of type mongo::BSONDBRef out of selected
    portions of a buffer read with gdb.Inferior.read_memory().

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        db_pointer = MongoBSONDBRef.unpack_from(self.val["_objdata"], view=objdata)
        yield (f"{i}", db_pointer.to_value())
    """

    namespace: MongoStringData
    oid: MongoOID

    @classmethod
    def unpack_from(cls, val: gdb.Value, /, *, view: memoryview) -> "MongoBSONDBRef":
        """Read a length-prefixed string and a 12-byte ObjectId starting from the beginning of the
        given buffer.
        """
        namespace = MongoStringData.from_pascalstring(val, view=view)
        offset = namespace.size.value + 4
        object_id = MongoOID.unpack_from(view[offset:])
        return cls(namespace=namespace, oid=object_id)

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::BSONDBRef."""
        typ = gdb.lookup_type("mongo::BSONDBRef")
        return gdb.Value(memoryview(self), typ)


setattr(MongoBSONDBRef, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoBSONDBRef)])


@dataclasses.dataclass
class MongoBSONRegEx(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::BSONRegEx.

    This class is useful for constructing gdb.Value objects of type mongo::BSONRegEx out of selected
    portions of a buffer read with gdb.Inferior.read_memory().

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        regexp = MongoBSONRegEx.unpack_from(self.val["_objdata"], view=objdata)
        yield (f"{i}", regexp.to_value())
    """

    pattern: MongoStringData
    flags: MongoStringData

    @classmethod
    def unpack_from(cls, val: gdb.Value, /, *, view: memoryview) -> "MongoBSONRegEx":
        """Read two null-terminated strings starting from the beginning of the given buffer."""
        pattern = MongoStringData.from_cstring(val, maxsize=len(view))
        offset = pattern.size.value + 1
        flags = MongoStringData.from_cstring(val + offset, maxsize=len(view) - offset)
        return cls(pattern=pattern, flags=flags)

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::BSONRegEx."""
        typ = gdb.lookup_type("mongo::BSONRegEx")
        return gdb.Value(memoryview(self), typ)


setattr(MongoBSONRegEx, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoBSONRegEx)])


@dataclasses.dataclass
class MongoBSONSymbol(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::BSONSymbol.

    This class is useful for constructing gdb.Value objects of type mongo::BSONSymbol out of
    selected portions of a buffer read with gdb.Inferior.read_memory().

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        symbol = MongoBSONSymbol.unpack_from(self.val["_objdata"], view=objdata)
        yield (f"{i}", symbol.to_value())
    """

    symbol: MongoStringData

    @classmethod
    def unpack_from(cls, val: gdb.Value, /, *, view: memoryview) -> "MongoBSONSymbol":
        """Read a length-prefixed string from the beginning of the given buffer."""
        symbol = MongoStringData.from_pascalstring(val, view=view)
        return cls(symbol=symbol)

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::BSONSymbol."""
        typ = gdb.lookup_type("mongo::BSONSymbol")
        return gdb.Value(memoryview(self), typ)


setattr(MongoBSONSymbol, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoBSONSymbol)])


# pylint: disable-next=too-few-public-methods
class UndefinedLabelerPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for literal undefined value."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    def to_string(self) -> str:
        return "undefined"


# pylint: disable-next=too-few-public-methods
class NullLabelerPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for literal null value."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    def to_string(self) -> str:
        return "null"


# pylint: disable-next=too-few-public-methods
class MinKeyLabelerPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for literal MinKey value."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    def to_string(self) -> str:
        return "MinKey()"


# pylint: disable-next=too-few-public-methods
class MaxKeyLabelerPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for literal MaxKey value."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val

    def to_string(self) -> str:
        return "MaxKey()"


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the BSON-related printers to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::MaxKeyLabeler", "^mongo::MaxKeyLabeler$",
                               MaxKeyLabelerPrinter)
    pretty_printer.add_printer("mongo::MinKeyLabeler", "^mongo::MinKeyLabeler$",
                               MinKeyLabelerPrinter)
    pretty_printer.add_printer("mongo::NullLabeler", "^mongo::NullLabeler$", NullLabelerPrinter)
    pretty_printer.add_printer("mongo::UndefinedLabeler", "^mongo::UndefinedLabeler$",
                               UndefinedLabelerPrinter)
