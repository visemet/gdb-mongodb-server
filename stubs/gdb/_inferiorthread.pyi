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
"""https://sourceware.org/gdb/onlinedocs/gdb/Threads-In-Python.html"""

import typing

from gdb._inferior import Inferior


class InferiorThread:

    name: str

    @property
    def num(self) -> int:
        ...

    @property
    def global_num(self) -> int:
        ...

    @property
    def ptid(self) -> typing.Tuple[int, int, int]:
        ...

    @property
    def inferior(self) -> Inferior:
        ...

    def is_valid(self) -> bool:
        ...

    def switch(self) -> None:
        ...

    def is_stopped(self) -> bool:
        ...

    def is_running(self) -> bool:
        ...

    def is_exited(self) -> bool:
        ...

    def handle(self) -> bytes:
        ...


def selected_thread() -> InferiorThread:
    ...
