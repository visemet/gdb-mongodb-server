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
"""Utility functions for gdb.Types and gdb.Values."""

import typing

import gdb


def gdb_lookup_value(symbol_name: str, /) -> typing.Optional[gdb.Value]:
    """Return the gdb.Value corresponding to the symbol name given."""
    if (symbol := gdb.lookup_symbol(symbol_name)[0]) is not None:
        return symbol.value()

    return None


def gdb_resolve_type(typ: gdb.Type, /) -> gdb.Type:
    """Look up the name of a C++ type with any typedefs, pointers, and references stripped.

    This function is useful in contexts where template arguments can be pointers because GDB may not
    load the fields of the templated entity otherwise.
    """
    typ = typ.strip_typedefs()

    while typ.code in (gdb.TYPE_CODE_PTR, gdb.TYPE_CODE_REF):
        typ = typ.target().strip_typedefs()

    if typ.code == gdb.TYPE_CODE_FUNC:
        return typ

    typename = typ.tag if typ.tag is not None else typ.name
    assert typename is not None
    return gdb.lookup_type(typename)
