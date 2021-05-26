.. _action_onhost_service:

Service's Actions on Cluster's Host
###################################

This spec is part of changes introduced in story :issue:`ADCM-1621`.

Main idea of this case is execution of service action on one particular host. 

“Used” Use Cases
----------------

This case is a detalisation of :ref:`action_onhost`.


Actors
------

* :term:`End User`
* :term:`Bundle Developer`

User Value
----------

This functionality allow :term:`End User` to make operation with service on one particular host. For example:

* Start service on one host
* Stop service on one host

Pre-Conditions
--------------

* :term:`End User` has ADCM with a :term:`Product` installed on some cluster

Post-Conditions
---------------

* :term:`End User` was able to run some action provided by :term:`Bundle Developer` on one host included in service



Flow of Events
--------------

1. :term:`Bundle Developer` adds action to a service like follows

.. code-block:: yaml

   - type: service
     name: My Supper Service
     version: "1.0"
     actions:
        restart: 
            display_name: "Restart service"
            type: job
            script_type: ansible
            script: restart.yaml
            host_action: true
            states:
                available: somestate
     components:
        mycomponent:
          constraint: [0,+]
        mycomponent2:
          constraint: [0,+]

2. :term:`End User` installs cluster from this :term:`Bundle`
3. :term:`End User` adds service
4. :term:`End User` adds hosts
5. :term:`End User` places "mycomponnet" or "mycomponent2" or both of them on a host
6. :term:`End User` sees the action "Restart service" on the host
7. :term:`End User` runs the action

Exceptions
~~~~~~~~~~

5. :term:`End User` chooses a host without "mycomponent" or "mycomponent2" installed on it.

   a. :term:`End User` sees no action "Restart service"
   b. The End

6. Service "My Supper Service" is not in state "somestate"

   a. :term:`End User` sees no action "Restart service"
   b. The End

.. warning:: We need to be sure, there is no troubles with mixing states. It should react on service state only.
