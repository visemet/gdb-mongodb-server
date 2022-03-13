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
"""Shim to expose the typing.Protocols defined in stubs/gdb/printing.pyi as concrete classes when
being referenced inside GDB.
"""

import typing

# pylint: disable=protected-access
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods

if typing.TYPE_CHECKING:
    import gdb.printing
    PrettyPrinterProtocol = gdb.printing.__PrettyPrinterProtocol
    SupportsChildren = gdb.printing.__SupportsChildren
    SupportsDisplayHint = gdb.printing.__SupportsDisplayHint
    SupportsToString = gdb.printing.__SupportsToString
else:

    class SupportsChildren(typing.Protocol):
        ...

    class SupportsDisplayHint(typing.Protocol):
        ...

    class SupportsToString(typing.Protocol):
        ...

    class PrettyPrinterProtocol(SupportsToString, SupportsChildren, typing.Protocol):
        ...
