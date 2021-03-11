.. _action_onhost_component:

Component's Actions on Cluster's Host
#####################################

This spec is part of changes introduced in story :issue:`ADCM-1508`.

Main idea of this case is execution of component action on one particular host. 

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

* :term:`End User` was able to run some action provided by :term:`Bundle Developer` on one host which has a component on it


Flow of Events
--------------

1. :term:`Bundle Developer` adds action to a component like follows

.. code-block:: yaml

   - type: service
     name: My Supper Service
     version: "1.0"
     components:
        mycomponent:
          constraint: [0,+]
          actions:
            restart: 
                display_name: "Restart mycomponent"
                type: job
                script_type: ansible
                script: restart.yaml
                host_action: true
                states:
                    available: somestate

2. :term:`End User` installs cluster from this :term:`Bundle`
3. :term:`End User` adds service
4. :term:`End User` adds hosts
5. :term:`End User` places "mycomponnet" on a host
6. :term:`End User` sees the action "Restart mycomponent" on the host
7. :term:`End User` runs the action

Exceptions
~~~~~~~~~~

5. :term:`End User` chooses a host without mycomponent installed on it

   a. :term:`End User` sees no action "Restart mycomonent"
   b. The End

6. Component "mycomponent" is not in state "somestate"

   a. :term:`End User` sees no action "Restart mycomonent"
   b. The End

.. warning:: We need to be sure, there is no troubles with mixing states. It should react on component state only.
