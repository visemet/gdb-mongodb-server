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
"""Pretty-printers for string-related data types."""

import typing

import gdb

from gdbmongo import stdlib_printers
from gdbmongo.printer_protocol import LazyString, SupportsDisplayHint, SupportsToString


class StdStringPrinter(SupportsDisplayHint, SupportsToString):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for std::string.

    This class wraps a gdb.libstdcxx.v6.printers.StdStringPrinter instance to support extracting the
    gdb.Value as a Python string. gdb.Value.__str__() returns a Python string according to how the
    value would be **printed** by GDB. It causes the value to be awkwardly double-quoted and
    possibly truncated due to the user's `set print elements` setting. This class avoids both of
    these issues by instead calling gdb.Value.string().
    """

    def __init__(self, val: gdb.Value) -> None:
        self.val = val

        typ = val.type.strip_typedefs()
        typename = typ.tag if typ.tag is not None else typ.name
        assert typename is not None
        self.printer = stdlib_printers.StdStringPrinter(typename, val)

    @staticmethod
    def display_hint() -> typing.Literal["string"]:
        return "string"

    def to_string(self) -> typing.Union[str, gdb.Value, LazyString, None]:
        return self.printer.to_string()

    def string(self) -> str:
        """Return the value as a Python string."""
        ret = self.to_string()
        assert ret is not None

        if isinstance(ret, gdb.Value):
            return ret.string()
        if isinstance(ret, LazyString):
            return ret.value().string()
        return ret
