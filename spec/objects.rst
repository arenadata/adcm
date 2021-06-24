Objects
=======

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
config              json    ?       ?        False            True               True               JSON field with config
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
