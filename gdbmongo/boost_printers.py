###
# Copyright 2023-present MongoDB, Inc.
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
"""Pretty-printers for boost:: types."""

import typing

import gdb

from gdbmongo.abseil_printers import gdb_resolve_type
from gdbmongo.printer_protocol import PrettyPrinterProtocol


class BoostOptionalPrinter(PrettyPrinterProtocol):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for boost::optional<T>."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.element_type = val.type.template_argument(0)
        self.is_initialized = bool(val["m_initialized"])
        self.val = val

        gdb_resolve_type(self.element_type)

    @staticmethod
    def display_hint() -> typing.Literal["array"]:
        return "array"

    def to_string(self) -> str:
        if self.is_initialized:
            return f"boost::optional<{self.element_type}>"

        return "boost::none"

    def children(self) -> typing.Iterator[typing.Tuple[str, gdb.Value]]:
        if self.is_initialized:
            # Ideally we would have returned `contained_value` in the to_string() method and skipped
            # defining a children() method at all. But that approach causes GDB to not display the
            # addresses for Xmethods like get() on std::unique_ptr and std::shared_ptr types for any
            # members within `contained_value`. We display the engaged boost::optional as if it was
            # an array of size 1 to keep the GDB output more compact as a compromise.
            storage = self.val["m_storage"]["dummy_"]["data"]
            contained_value = storage.cast(self.element_type.pointer()).dereference()
            yield ("", contained_value)


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the Boost printers to the pretty printer collection given."""
    pretty_printer.add_printer("boost::optional", "^boost::optional<.*>$", BoostOptionalPrinter)