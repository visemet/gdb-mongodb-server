###
# Copyright 2016-present MongoDB, Inc.
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
"""Pretty-printer for "decorated" types in the MongoDB Server.

This includes MongoDB types like ServiceContext, Client, and OperationContext. Decorated types have
a memory compartment and a registration scheme where other .cpp files can be allocated an offset
into the memory compartment.

For example, after the DecorationContainerPrinter pretty printer has been registered in GDB, the
decorated values on the global ServiceContext can be displayed with the following command:

.. code-block:: gdb

    print 'mongo::(anonymous namespace)::globalServiceContext'._decorations
"""

import re

import gdb

from gdbmongo import stdlib_printers


class DecorationContainerPrinter:
    # pylint: disable=missing-function-docstring
    """Pretty-printer for mongo::DecorationContainer<DecoratedType>.

    This includes MongoDB types like ServiceContext, Client, and OperationContext."""

    symbol_name_regexp = re.compile(r"^(.*) in ")
    type_name_regexp = re.compile(r"^(.*[\w>])([\s\*]*)$")

    def __init__(self, val):
        self.val = val

        decoration_registry = val["_registry"]
        self.decorations_info = decoration_registry["_decorationInfo"]
        self.decorations_storage = val["_decorationData"]

        registry_type = decoration_registry.dereference().type
        self.constructor_regexp = re.compile(
            fr"^void {registry_type.name}::constructAt<\s*(.*)\s*>\(void\*\)$")

    def to_string(self):
        iterator = stdlib_printers.StdVectorPrinter("std::vector", self.decorations_info).children()
        length = iterator.finish - iterator.item
        return f"{self.val.type.name} with {stdlib_printers.num_elements(length)}"

    def children(self):
        decorations_storage = stdlib_printers.UniquePointerPrinter("std::unique_ptr",
                                                                   self.decorations_storage).pointer

        iterator = stdlib_printers.StdVectorPrinter("std::vector", self.decorations_info).children()
        for (index, (_, descriptor)) in enumerate(iterator):
            descriptor_offset = int(descriptor["descriptor"]["_index"])
            decoration_value = decorations_storage[descriptor_offset]
            decoration_type = self._lookup_decoration_type(
                self._get_decoration_type_name(descriptor), descriptor)

            # decoration_value.cast(decoration_type) may not be an addressable object so we get its
            # address through the unsigned char[] representation of the value.
            yield (
                f"[{index}] = ({decoration_type.pointer()}) {hex(int(decoration_value.address))}",
                decoration_value.cast(decoration_type))

    def _lookup_decoration_type(self, type_name: str, descriptor: gdb.Value) -> gdb.Type:
        """Return the type of the decoration value."""
        # We cannot use gdb.lookup_type() when the decoration type is a pointer type, e.g.
        # ServiceContext::declareDecoration<VectorClock*>(). gdb.parse_and_eval() is one of the few
        # ways to convert a type expression into a gdb.Type value. Some care is taken to quote the
        # non-pointer portion of the type so resolution for a type defined within an anonymous
        # namespace works correctly.
        escaped = self.type_name_regexp.sub(r"'\1'\2*", type_name)
        return gdb.parse_and_eval(f"({escaped}) {int(descriptor.address)}").type.target()

    def _get_decoration_type_name(self, descriptor: gdb.Value) -> str:
        """Return the name of the decoration type."""
        function = descriptor["constructor"]
        address = int(function.dereference().address)

        # We use the `info symbol <address>` command to retrieve the type name for a couple reasons:
        #
        #   1. Unlike gdb.libstdcxx.v6.printers.function_pointer_to_name(), the `info symbol`
        #      command consults the minimal symbol table (aka msymtabs). This enables the command to
        #      prefer certain symbol names over what `gdb.block_for_pc(address).function.name`
        #      naively would have returned in its place. The difference in behavior has been
        #      observed to affect the std::unique_ptr and std::shared_ptr types, both of which are
        #      commonly used as decoration values. Using the `info symbol` command appears to keep
        #      the decoration types more consistent with their source code definitions.
        #
        #   2. While gdb.Type.__str__() also consults the minimal symbol table, its formatting for
        #      the type name may prohibit resolving the underlying decoration type and seemingly
        #      cannot be configured. The result from `str(function)` would omit any default template
        #      arguments. Types such as std::unique_ptr<mongo::AuthorizationManager> must explicitly
        #      include std::default_delete<mongo::AuthorizationManager> as a second template
        #      argument to always be recognized by GDB.
        symbol_info = gdb.execute(f"info symbol {address}", to_string=True).rstrip()
        if (match := self.symbol_name_regexp.match(symbol_info)) is None:
            raise ValueError(
                f"Unable to extract symbol name: {symbol_info}; str() would have returned"
                f" '{str(function)}' and function_pointer_to_name() would have returned"
                f" '{stdlib_printers.function_pointer_to_name(function)}'; perhaps we should"
                " consider adding a fallback mechanism?")

        type_name = match.group(1)
        return self.constructor_regexp.match(type_name).group(1)


def add_printers(pretty_printer):
    """Add the DecorationContainerPrinter to the pretty printer collection given."""
    pretty_printer.add_printer("mongo::DecorationContainer", "^mongo::DecorationContainer<.*>$",
                               DecorationContainerPrinter)
