Changelog
=========

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
