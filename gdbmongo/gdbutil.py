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


def gdb_is_libthread_db_loaded() -> bool:
    """Return True if the libthread_db library is initialized, and return False otherwise.

    Thread debugging in GDB is not available when either (a) the libthread_db library is not found
    or (b) when the found version is not compatible with the libpthread library. Only when thread
    debugging is available can GDB inspect thread-local variables, for example.
    """
    try:
        gdb.execute("maintenance check libthread-db", to_string=True)
        return True
    except gdb.error as err:
        if err.args[0] != "No libthread_db loaded":
            raise

        return False


def gdb_are_debug_symbols_loaded() -> bool:
    """Return False if debug symbols are not present, and return True otherwise.

    This function is not guaranteed to return False when debug symbols only exist for some of the
    program's shared libraries. Instead, this function returning False should imply to the caller
    that looking up symbols, types, values, etc. in GDB is unlikely to succeed and would preferably
    be avoided.
    """
    try:
        ret = gdb.execute("info address main", to_string=True)
        return not ret.endswith(" in a file compiled without debugging.\n")
    except gdb.error as err:
        if not err.args[0].startswith("No symbol "):
            raise

        return False
