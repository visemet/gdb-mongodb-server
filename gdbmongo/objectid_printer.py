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
"""Pretty-printer for the mongo::OID type."""

import ctypes
import dataclasses
import typing

import gdb

from gdbmongo.printer_protocol import SupportsToString


@dataclasses.dataclass
class MongoOID(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::OID.

    This class is useful for constructing gdb.Value objects of type mongo::OID out of selected
    portions of a buffer read with gdb.Inferior.read_memory(). These synthetic gdb.Values can then
    be formatted by ObjectIdPrinter like normal.

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        object_id = MongoOID.unpack_from(objdata)
        yield (f"{i}", object_id.to_value())
    """

    if typing.TYPE_CHECKING:
        data: ctypes.Array[ctypes.c_char]
    else:
        data: ctypes.c_char * 12

    @classmethod
    def unpack_from(cls, buffer: memoryview, /) -> "MongoOID":
        """Read a 12-byte ObjectId starting from the beginning of the given buffer."""
        return cls.from_buffer(buffer)

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::OID."""
        typ = gdb.lookup_type("mongo::OID")
        return gdb.Value(memoryview(self), typ)


setattr(MongoOID, "_fields_", [(field.name, field.type) for field in dataclasses.fields(MongoOID)])


# pylint: disable-next=too-few-public-methods
class ObjectIdPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::OID."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val
        self.data = val["_data"]

    def to_string(self) -> str:
        unsigned_char = gdb.lookup_type("unsigned char")
        data = bytearray(int(self.data[i].cast(unsigned_char)) for i in range(12))
        return f'ObjectId("{data.hex()}")'


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the ObjectIdPrinter to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::OID", "^mongo::OID$", ObjectIdPrinter)
