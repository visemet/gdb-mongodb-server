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
"""Pretty-printer for the mongo::StaticImmortal<T> type."""

import gdb

from gdbmongo.boost_printers import SingletonPrinterBase
from gdbmongo.gdbutil import gdb_resolve_type
from gdbmongo.printer_protocol import PrettyPrinterProtocol


class StaticImmortalPrinter(PrettyPrinterProtocol, SingletonPrinterBase):
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::StaticImmortal<T>."""

    def __init__(self, val: gdb.Value, /) -> None:
        self.element_type = val.type.template_argument(0)
        self.val = val

        gdb_resolve_type(self.element_type)

    def to_string(self) -> str:
        return f"mongo::StaticImmortal<{self.element_type}>"

    def value(self) -> gdb.Value:
        storage = self.val["_storage"]["__data"]
        contained_value = storage.cast(self.element_type.pointer()).dereference()
        return contained_value


def add_printers(pretty_printer: gdb.printing.RegexpCollectionPrettyPrinter, /) -> None:
    """Add the StaticImmortalPrinter to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::StaticImmortal", "^mongo::StaticImmortal<.*>$",
                               StaticImmortalPrinter)
