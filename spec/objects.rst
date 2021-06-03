Objects
=======

.. _object-group:

Group
~~~~~

Group is an entity wich is capable to hold some number of host in it and connect it to some objects. Besides the group allow to pin a subset of object config and provide a way to change the config.

Endpoint: */group*

=================== ======= ======= ======== ================ ================== ================== ===========
Name                Type    Default Nullable :term:`Required` :term:`POSTable`   :term:`Changeable` Description
=================== ======= ======= ======== ================ ================== ================== ===========
id                  integer auto    False    False            False              False              Object id.
object              GFK     null    False    True             True               False              General FK which represent a FK to any object (but not host itself).
name                string  null    False    True             True               True               Name of object.
description         text    null    True     False            True               True               Extended information provided by user.
host                M2M     null    True     False            True               True               M2M link to Host object.
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
