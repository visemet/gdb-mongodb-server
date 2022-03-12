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
"""https://sourceware.org/gdb/onlinedocs/gdb/Values-From-Inferior.html"""

import typing

from gdb._type import Type

ConstructibleFrom = bool | int | float | str | Value


class Value(typing.SupportsInt, typing.SupportsFloat):

    def __init__(self, val: ConstructibleFrom, /) -> None:
        ...

    def __bool__(self) -> bool:
        ...

    def __int__(self) -> int:
        ...

    def __float__(self) -> float:
        ...

    def __str__(self) -> str:
        ...

    @typing.overload
    def __getitem__(self, field: str) -> Value:
        ...

    @typing.overload
    def __getitem__(self, idx: int) -> Value:
        ...

    def __lt__(self, other: object) -> bool:
        ...

    def __le__(self, other: object) -> bool:
        ...

    def __eq__(self, other: object) -> bool:
        ...

    def __ne__(self, other: object) -> bool:
        ...

    def __gt__(self, other: object) -> bool:
        ...

    def __ge__(self, other: object) -> bool:
        ...

    def __add__(self, other: ConstructibleFrom) -> Value:
        ...

    def __sub__(self, other: ConstructibleFrom) -> Value:
        ...

    @property
    def address(self) -> Value:
        ...

    @property
    def is_optimized_out(self) -> bool:
        ...

    @property
    def type(self) -> Type:
        ...

    @property
    def dynamic_type(self) -> Type:
        ...

    def cast(self, typ: Type, /) -> Value:
        ...

    def dynamic_cast(self, typ: Type, /) -> Value:
        ...

    def reinterpret_cast(self, typ: Type, /) -> Value:
        ...

    def dereference(self) -> Value:
        ...

    def referenced_value(self) -> Value:
        ...
