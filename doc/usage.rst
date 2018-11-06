Examples
========

Regex matching
--------------

Removes build tags created by CI:


.. code-block:: yaml

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

.. code-block:: yaml

   repositories:
     "docker.glorpen.eu/test":
       # ... other groups ...
       other:
         type: max
         max_items: 0


Semver tags
-----------

http://semver.org/
