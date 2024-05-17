==================
gdb-mongodb-server
==================

About
=====

The *gdbmongo* package contains GDB pretty printers and commands for
debugging the MongoDB Server. Its primary target audience is MongoDB
employees.

Motivation
----------

The *gdbmongo* package is mostly born out of joy from tinkering with
low-level constructs while writing GDB pretty printers. There are some
explicit areas for what it aims to achieve:

1. GDB pretty printers and commands which only work against live MongoDB
   processes are of limited value. This is because the hang analyzer is
   only granted enough time in Evergreen to save a core file for each of
   the lingering processes. Further analysis is deferred until later by
   making use of these saved core files. GDB pretty printers and
   commands which are implemented by walking in-memory data structures
   and not by executing C++ code **can run against core dumps** and are
   therefore more widely applicable.

2. New versions of the MongoDB Server are released regularly. Each new
   git branch fragments the tooling for testing the server. This can
   cause development on older branches to feel foreign and awkward
   because so many new enhancements were made in the meantime. Flipping
   the model so there’s **a single version which attempts to work with
   all supported MongoDB versions** can potentially enable more things
   to “just work.” Another way to think about it is that the new GDB
   pretty printers and commands may not be getting built for new MongoDB
   Server functionality and instead may be getting built for a
   newly-recognized debugging need.

Installation
============

The *gdbmongo* package must be loaded into the Python installation that
the GDB process is running. In particular, launching ``gdb`` from within
a Python virtual environment won’t give the GDB process access to the
Python packages defined within the virtual environment. This is because
``gdb`` is dynamically linked against *libpython* and therefore always
uses the site-packages of the base installation.

Adding the following snippet to a .gdbinit file will cause ``gdb`` at
launch time to attempt to install the *gdbmongo* package if it isn’t
already installed.

.. code-block:: python

    # In your ~/.gdbinit:
    python
    try:
        import gdbmongo
    except ImportError:
        import sys
        if sys.prefix.startswith("/opt/mongodbtoolchain/"):
            import subprocess
            subprocess.run([sys.prefix + "/bin/python3", "-m", "pip", "install", "gdbmongo"], check=True)
            import gdbmongo
        else:
            import warnings
            warnings.warn("Not attempting to install gdbmongo into non MongoDB toolchain Python")

    if "gdbmongo" in dir():
        gdbmongo.register_printers()
    end

If you don’t plan to use the GDB pretty printers defined in the
mongodb/mongo repository then you may want to consider enabling some of
the other printers defined by the *gdbmongo* package by default.

.. pull-quote::

    register_printers(\*, essentials=True, stdlib=False, abseil=False, boost=False, mongo_extras=False)
        Register the pretty printers defined by the gdbmongo package with GDB itself.

        The pretty printer collections other than gdbmongo-essentials are defaulted to off to avoid
        conflicting with the pretty printers defined in the mongodb/mongo repository.

Regardless of whether you choose to enable these other pretty printers
by default, each of the gdbmongo-\* pretty printer collections can still
be enabled later on within GDB. For example, the gdbmongo-mongo-extras
pretty printer collection can be enabled with the following command:

.. code-block::

    (gdb) enable pretty-printer global gdbmongo-mongo-extras

*Tip*: Use ``info pretty-printer``, ``enable pretty-printer``,
``disable pretty-printer``, and ``print /r`` to inspect and toggle the
state of any GDB pretty printers.

Usage
=====

The *gdbmongo* package is a nascent GDB extension and quite limited in
what it can do right now. But, if you’re looking to dump the contents of
the global ``LockManager`` in a core dump, then you can run the
following commands:

.. code-block:: python

    (gdb) python lock_mgr = gdbmongo.LockManagerPrinter.from_global()
    (gdb) python print(lock_mgr.val)
