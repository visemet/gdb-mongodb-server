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
"""https://sourceware.org/gdb/onlinedocs/gdb/Frames-In-Python.html"""

import typing

from gdb._symbol import Symbol


class Frame:

    def is_valid(self) -> bool:
        ...

    def name(self) -> typing.Optional[str]:
        ...

    def pc(self) -> int:
        ...

    def function(self) -> typing.Optional[Symbol]:
        ...

    def older(self) -> typing.Optional[Frame]:
        ...

    def newer(self) -> typing.Optional[Frame]:
        ...

    def select(self) -> None:
        ...

    def level(self) -> int:
        ...


def selected_frame() -> Frame:
    ...


def newest_frame() -> Frame:
    ...
