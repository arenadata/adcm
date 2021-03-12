.. _action_onhost_target:

Target group in inventory
#########################

This spec is part of changes introduced in story :issue:`ADCM-1623`.

We need special group in inventory to provide information for :term:`Bundle Developer` about which of host has been choosed by :term:`End User`


“Used” Use Cases
----------------

This case is a detalisation of :ref:`action_onhost`.

Actors
------

* :term:`End User`
* :term:`Bundle Developer`

User Value
----------

This functionality allow to be sure information passed by :term:`End User` is available for :term:`Bundle Developer`.

Pre-Conditions
--------------

* :term:`End User` has ADCM with a :term:`Product` installed on some cluster.

Post-Conditions
---------------

* there a new group "target" in inventory file with host choosed by :term:`End User`


Flow of Events
--------------

1. :term:`Bundle Developer` adds action to some object in :term:`Product` bundle acording to any of the cases:
  * :ref:`action_onhost_cluster`
  * :ref:`action_onhost_service`
  * :ref:`action_onhost_component`
2. :term:`End User` run "on host" action according to any of the cases
  * :ref:`action_onhost_cluster`
  * :ref:`action_onhost_service`
  * :ref:`action_onhost_component`
3. Action executes with right inventory
