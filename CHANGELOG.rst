Changelog
=========

0.15.2 (2025-02-02)
-------------------

* Fix listing decorations of upcoming MongoDB 8.1. This includes accessing LockManager on global
  ServiceContext.

0.15.1 (2024-05-19)
-------------------

* Fix detecting libstdc++ version for Clang sanitizer builds.
* Fix listing decorations of MongoDB 8.0. This includes accessing LockManager on global
  ServiceContext.

0.15.0 (2024-04-29)
-------------------

* Support dumping LockManager from core dump of MongoDB 8.0.
* Fix mongo::StringData pretty printer and mongo::BSONObj pretty printer which consumes it.

0.14.0 (2023-09-30)
-------------------

* Include OperationContext* in output for LockManager dump.

0.13.0 (2023-09-29)
-------------------

* Include thread’s name and number in output for LockManager dump.
* Fix detecting compiler version when cross-platform debugging.

0.12.0 (2023-09-22)
-------------------

* Support displaying thread names in core dump of MongoDB 4.4, 5.0, and 6.0.

0.11.0 (2023-09-16)
-------------------

* Support displaying contents of partitions within CursorManager.

0.10.0 (2023-09-03)
-------------------

* Support dumping LockManager from core dump of MongoDB 7.1.

0.9.0 (2023-08-26)
------------------

* Support dumping LockManager from core dump of MongoDB 7.0.

0.8.1 (2023-03-04)
------------------

* Fix two Python exceptions from thread names logic when no program or core dump was loaded.
* Fix boost::optional pretty printer for scalar types.

0.8.0 (2023-02-04)
------------------

* Always register gdbmongo pretty printers with GDB itself but continue defaulting them to off.
* Support displaying thread names in core dump of MongoDB 6.2.

0.7.0 (2022-12-24)
------------------

* Support binaries built with MongoDB v4 toolchain.

0.6.0 (2022-11-18)
------------------

* Support dumping LockManager from core dump of MongoDB 6.2.
* Fix resource type names in output of MongoDB 4.4.15, 5.0.10, and 6.0.0.

0.5.1 (2022-08-25)
------------------

* Fix detecting MongoDB toolchain from --install-action=hardlink executables.

0.5.0 (2022-07-31)
------------------

* Format BSON binary subtype 4 as UUID.
* Include ErrorExtraInfo in output for Status and StatusWith<T>.

0.4.0 (2022-04-09)
------------------

* Support detecting libstdc++ version in MongoDB binaries back to 4.2.0 and 4.4.0.
* Support decoding BSONObjs even when they contain dates exceeding datetime.MAXYEAR (= 9999).

0.3.0 (2022-03-26)
------------------

* Include database name in dump of DatabaseShardingState ResourceMutexes.
* Avoid truncating namespace strings in LockManager dump.

0.2.0 (2022-03-05)
------------------

* Support dumping LockManager from core dump of MongoDB 4.2, 4.4, and 5.0.

0.1.0 (2022-02-26)
------------------

* Initial release.
* Support dumping LockManager from core dump of MongoDB 5.3.
