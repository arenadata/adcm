ADCM Componets
##############

UI
===

The frontend part of ADCM. Based on Angular Framework and meterial design.

Job Executor
============

Job executor of ADCM is quite simple. It just a script to prepare data for Ansible and some script to handle ansible-playbook command.

Ansible
=======

This part of ADCM responses for all operations on hosts. Playbooks are delivered of bundles.

Currently we are using Ansible 2.8.x version.

WSGI Backend
============

This is a part of backend repsponsible for most operations. It based on Django ORM framework and Django REST Framework (DRF).

Resident Backend
================

Resident Backend part, also known as Status Server (SS) is part of ADCM based on Golang platform. It responsible for event fiding from Django to UI over websocket protocol and for handling of statuses.

Nginx
=====

It is a standart Nginx web server who route request to Resident Backend and WSGI Backend and serve static files.
