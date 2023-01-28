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
"""https://sourceware.org/gdb/onlinedocs/gdb/Inferiors-In-Python.html"""

import typing

from _typeshed import ReadableBuffer

from gdb._architecture import Architecture
from gdb._inferiorthread import InferiorThread
from gdb._progspace import Progspace
from gdb._value import Value


class Inferior:

    @property
    def progspace(self) -> Progspace:
        ...

    def threads(self) -> typing.Tuple[InferiorThread, ...]:
        ...

    def architecture(self) -> Architecture:
        ...

    def read_memory(self, address: int | Value, length: int | Value, /) -> memoryview:
        ...

    def search_memory(self, address: int | Value, length: int | Value, pattern: ReadableBuffer,
                      /) -> typing.Optional[int]:
        ...


def selected_inferior() -> Inferior:
    ...
