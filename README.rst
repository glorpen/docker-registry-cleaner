=======================
Docker Registry Cleaner
=======================

Smart Docker Registry cleaner.

State of Docker Registry
========================

Workarounds for version 2.6.2 of Docker Registry.

Safe tag deletion
-----------------

Docker Registry has no native support for deleting single tag from an image.

Fortunatelly it is possible to workaround this problem so Docker Registry Cleaner will **safely** remove tag from image, without removing image itself.
The process is quite simple:

- find tags to remove
- upload fake image
- re-tag found tags to new image
- remove image with REST API call

Empty repositories
------------------

There is no way to remove repository using REST API, even one without tags.

Removing empty repository should be handled on registry side, by your docker-registry image, eg. on GC run.

See https://hub.docker.com/r/glorpen/registry/ .

Examples
========

Regex matching
--------------

Removes build tags created by CI:


.. sourcecode:: yaml

   patterns:
     latest:
       - "latest"
     ci:
       "r-([0-9]+)": "\\1"
       "build-([0-9]+)": "\\1"
   
   repositories:
     "docker.glorpen.eu/test":
       latest:
         type: pattern
         pattern: ci
         max_items: 10

Remove unknown tags
-------------------

Removes tags that are not known for groups before it.

.. sourcecode:: yaml

   repositories:
     "docker.glorpen.eu/test":
       # ... other groups ...
       other:
         type: max
         max_items: 0


Semver tags
-----------

http://semver.org/
