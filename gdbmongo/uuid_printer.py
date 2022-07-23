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
"""Pretty-printer for the mongo::UUID type."""

import ctypes
import dataclasses
import typing
import uuid

import gdb

from gdbmongo.printer_protocol import SupportsToString


# pylint: disable-next=invalid-name
# pylint: disable-next=too-few-public-methods
class c_uint8(ctypes.c_uint8):
    """Wrapper class for ctypes.c_uint8 to avoid implicit conversion to int."""


@dataclasses.dataclass
class MongoUUID(ctypes.Structure):
    """Structure with a memory layout compatible with that of mongo::UUID.

    This class is useful for constructing gdb.Value objects of type mongo::UUID out of selected
    portions of a buffer read with gdb.Inferior.read_memory(). These synthetic gdb.Values can then
    be formatted by UUIDPrinter like normal.

    .. code-block:: python

        objdata = gdb.selected_inferior().read_memory(self.val["_objdata"], objsize)
        uuid = MongoUUID.unpack_from(objdata)
        yield (f"{i}", uuid.to_value())
    """

    if typing.TYPE_CHECKING:
        uuid: ctypes.Array[c_uint8]
    else:
        uuid: c_uint8 * 16

    @classmethod
    def unpack_from(cls, buffer: memoryview, /) -> "MongoUUID":
        """Read a 16-byte UUID starting from the beginning of the given buffer."""
        return cls.from_buffer(buffer)

    def to_value(self) -> gdb.Value:
        """Convert the structure to a gdb.Value of type mongo::UUID."""
        typ = gdb.lookup_type("mongo::UUID")
        return gdb.Value(memoryview(self), typ)


setattr(MongoUUID, "_fields_",
        [(field.name, field.type) for field in dataclasses.fields(MongoUUID)])


# pylint: disable-next=too-few-public-methods
class UUIDPrinter(SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::UUID."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.val = val
        self.uuid = val["_uuid"]["_M_elems"]

    def to_string(self) -> str:
        data = bytes([int(self.uuid[i]) for i in range(16)])
        return f'UUID("{uuid.UUID(bytes=data)}")'


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the UUIDPrinter to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::UUID", "^mongo::UUID$", UUIDPrinter)
