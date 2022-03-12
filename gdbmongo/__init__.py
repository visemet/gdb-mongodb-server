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
"""The gdbmongo package contains GDB pretty printers and commands for debugging the MongoDB Server.

Its primary target audience is MongoDB employees.
"""

import typing

try:
    import gdb
except ImportError:
    # There is no gdb module when we're running the Python unit tests. We skip doing the imports for
    # the actual GDB pretty printers because they expect there to always be a gdb module defined.
    pass
else:
    from gdbmongo.interaction import register_printers
    from gdbmongo.lock_manager_printer import LockManagerPrinter

__version__: typing.Optional[str]

try:
    from gdbmongo._version import version as __version__
except ImportError:
    # The package is not installed so we don't bother giving it a version number.
    __version__ = None
