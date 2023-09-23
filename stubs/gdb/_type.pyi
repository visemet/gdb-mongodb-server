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
"""https://sourceware.org/gdb/onlinedocs/gdb/Types-In-Python.html"""

import enum
import typing


class TypeCode(enum.IntEnum):
    """https://sourceware.org/git/?p=binutils-gdb.git;a=blob;f=gdb/gdbtypes.h;hb=refs/tags/gdb-8.3.1-release#l90"""

    TYPE_CODE_BITSTRING = -1
    TYPE_CODE_PTR = 1
    TYPE_CODE_ARRAY = 2
    TYPE_CODE_STRUCT = 3
    TYPE_CODE_UNION = 4
    TYPE_CODE_ENUM = 5
    TYPE_CODE_FLAGS = 6
    TYPE_CODE_FUNC = 7
    TYPE_CODE_INT = 8
    TYPE_CODE_FLT = 9
    TYPE_CODE_VOID = 10
    TYPE_CODE_SET = 11
    TYPE_CODE_RANGE = 12
    TYPE_CODE_STRING = 13
    TYPE_CODE_ERROR = 14
    TYPE_CODE_METHOD = 15
    TYPE_CODE_METHODPTR = 16
    TYPE_CODE_MEMBERPTR = 17
    TYPE_CODE_REF = 18
    TYPE_CODE_RVALUE_REF = 19
    TYPE_CODE_CHAR = 20
    TYPE_CODE_BOOL = 21
    TYPE_CODE_COMPLEX = 22
    TYPE_CODE_TYPEDEF = 23
    TYPE_CODE_NAMESPACE = 24
    TYPE_CODE_DECFLOAT = 25
    TYPE_CODE_INTERNAL_FUNCTION = 27


class Field:

    @property
    def bitpos(self) -> typing.Optional[int]:
        ...

    # The `enumval` property is omitted here because it is assumed gdb.Type.fields() will only be
    # used for TYPE_CODE_STRUCT C++ types. The `enumval` property is mutually exclusive with the
    # `bitpos` property.
    # https://sourceware.org/git/?p=binutils-gdb.git;a=blob;f=gdb/python/py-type.c;hb=refs/tags/gdb-12.1-release#l184

    @property
    def name(self) -> typing.Optional[str]:
        ...

    @property
    def artificial(self) -> bool:
        ...

    @property
    def is_base_class(self) -> bool:
        ...

    @property
    def bitsize(self) -> int:
        ...

    @property
    def type(self) -> typing.Optional[Type]:
        ...

    @property
    def parent_type(self) -> Type:
        ...


class Type:

    @property
    def code(self) -> TypeCode:
        ...

    @property
    def name(self) -> typing.Optional[str]:
        ...

    @property
    def tag(self) -> typing.Optional[str]:
        ...

    def fields(self) -> typing.List[Field]:
        ...

    def unqualified(self) -> Type:
        ...

    def reference(self) -> Type:
        ...

    def pointer(self) -> Type:
        ...

    def strip_typedefs(self) -> Type:
        ...

    def target(self) -> Type:
        ...

    def template_argument(self, n: int, /) -> Type:
        ...


def lookup_type(typename: str, /) -> Type:
    ...
