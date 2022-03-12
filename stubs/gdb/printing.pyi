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
"""https://sourceware.org/gdb/onlinedocs/gdb/Pretty-Printing-API.html
https://sourceware.org/gdb/onlinedocs/gdb/Writing-a-Pretty_002dPrinter.html
https://sourceware.org/gdb/onlinedocs/gdb/gdb_002eprinting.html
"""

import typing

from gdb._objfile import Objfile
from gdb._progspace import Progspace
from gdb._value import Value


class SupportsDisplayHint(typing.Protocol):

    def display_hint(
            self
    ) -> typing.Literal["string"] | typing.Literal["array"] | typing.Literal["map"] | None:
        ...


class SupportsToString(typing.Protocol):

    def to_string(self) -> str | Value | None:
        ...


class SupportsChildren(typing.Protocol):

    def children(self) -> typing.Iterator[typing.Tuple[str, Value]]:
        ...


class PrettyPrinterProtocol(SupportsToString, SupportsChildren, typing.Protocol):

    def __init__(self, val: Value, /) -> None:
        ...


class PrettyPrinter:

    def __init__(self, name: str,
                 subprinters: typing.Optional[typing.Iterator[SubPrettyPrinter]] = None, /) -> None:
        self.name = name
        self.subprinters = subprinters
        self.enabled: bool = True

    def __call__(self, val: Value, /) -> SupportsToString | SupportsChildren | None:
        ...


class SubPrettyPrinter:

    def __init__(self, name: str, /) -> None:
        self.name = name
        self.enabled: bool = True


class RegexpCollectionPrettyPrinter(PrettyPrinter):

    def __init__(self, name: str) -> None:
        ...

    def add_printer(self, name: str, regexp: str,
                    gen_printer: typing.Type[SupportsToString] | typing.Type[SupportsChildren],
                    /) -> None:
        ...


class FlagEnumerationPrinter(PrettyPrinter):

    def __init__(self, name: str, /) -> None:
        ...


def register_pretty_printer(obj: Objfile | Progspace | None,
                            printer: typing.Callable[[Value],
                                                     SupportsToString | SupportsChildren | None],
                            replace: bool = False) -> None:
    ...
