Objects
=======

.. _object-object-config:

Object Config
~~~~~~~~~~~~~

ObjectConfig is an object that contains the ID of the current and previous config

Endpoint: */object-config*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    False            False              False              Object id.
current             FK      null    False    False            False              False              FK on `ConfigLog` object
previous            FK      null    False    False            False              False              FK on `ConfigLog` object
history             link    null    False    False            False              False              Link on list `ConfigLog` object for this object
url                 link    null    False    False            False              False              Reference to this object
=================== ======= ======= ======== ================ ================== ================== ===========

API Calls Allowed
^^^^^^^^^^^^^^^^^

============= =======
Operation     Allowed
============= =======
GET           True
LIST          True
POST          False
PUT           False
PATCH         False
DELETE        False
============= =======

.. _object-config-log:

Config Log
~~~~~~~~~~~~~

ObjectLog is an object that contains object configurations

Endpoint: */config-log*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    False            False              False              Object id.
date                date    auto    False    False            False              False              Object creation date
obj_ref             FK      null    False    True             True               False              FK on `ObjectConfig` object
description         string  ''      True     False            True               True               Description
config              json    {}      False    False            True               True               Configuration
attr                json    {}      False    False            True               True               Additional attributes
url                 link    null    False    False            False              False              Reference to this object
=================== ======= ======= ======== ================ ================== ================== ===========

API Calls Allowed
^^^^^^^^^^^^^^^^^

============= =======
Operation     Allowed
============= =======
GET           True
LIST          True
POST          True
PUT           False
PATCH         False
DELETE        False
============= =======

.. _object-config-group:

Config Group
~~~~~~~~~~~~

Group is an entity wich is capable to hold some number of host in it and connect it to some objects. Besides the group allow to pin a subset of object config and provide a way to change the config.

Endpoint: */config-group*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    False            False              False              Object id.
object_id           integer null    False    True             True               False              Object id for object
object_type         string  null    False    True             True               False              Object type (`cluster`, `service`, `component`, `provider`)
name                string  null    False    True             True               True               Name of object.
description         text    null    True     False            True               True               Extended information provided by user.
hosts               M2M     null    True     False            False              False              M2M link to Host object.
config              FK      null    True     False            False              True               FK field on ObjectConfig object
url                 link    null    False    False            False              False              Reference to this object
=================== ======= ======= ======== ================ ================== ================== ===========

.. note::
   TODO: Define what is this the config in the group object (diff or full object) and should it has history.


API Calls Allowed
^^^^^^^^^^^^^^^^^

============= =======
Operation     Allowed
============= =======
GET           True
LIST          True
POST          True
PUT           True
PATCH         True
DELETE        True
============= =======

Host Group
~~~~~~~~~~~~

.. _object-host-group:

Endpoint: */host-group*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    False            False              False              Object ID.
host                FK      null    False    True             True               True               `Host` object ID
group               FK      null    False    True             True               True               `ConfigGroup` object ID
=================== ======= ======= ======== ================ ================== ================== ===========

.. note::
   Constrains for :term:`Changeable`, the host cannot be a member of different groups of the same object,
   when you try to modify an object in this way, you will get an error: "HOST_GROUP_ERROR": "host already is a member of another group of this object"


API Calls Allowed
^^^^^^^^^^^^^^^^^

============= =======
Operation     Allowed
============= =======
GET           True
LIST          True
POST          True
PUT           True
PATCH         True
DELETE        True
============= =======
