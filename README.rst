=======================
Docker Registry Cleaner
=======================

.. image:: https://travis-ci.com/glorpen/docker-registry-cleaner.svg?branch=master
    :target: https://travis-ci.com/glorpen/docker-registry-cleaner
    :alt: Build Status
.. image:: https://readthedocs.org/projects/docker-registry-cleaner/badge/?version=latest
    :target: https://docker-registry-cleaner.readthedocs.io/en/latest/
    :alt: Doc Status

Smart Docker Registry cleaner.

--------
Features
--------

- removing tags
- running garbage-collect
- cleaning empty repos (without tags)
- cleaning tags with regex and semantic versioning
- removing unknown tags
- no configuration changes in real registry service

Container
=========

Container version uses bundled Docker Registry binary, see _`Bundled registry versions` table below.

Bundled registry versions
-------------------------

==========  ==========
  cleaner    registry
==========  ==========
1.0.0       2.7.1
==========  ==========

---------------------
Official repositories
---------------------

GitHub: https://github.com/glorpen/docker-registry-cleaner

BitBucket: https://bitbucket.org/glorpen/docker-registry-cleaner

Docker Hub: https://hub.docker.com/r/glorpen/registry-cleaner

------------------------
State of Docker Registry
------------------------

Workarounds for versions 2.6+ of Docker Registry.

See https://github.com/docker/distribution/issues/1811

Safe tag deletion
=================

Docker Registry has no native support for deleting single tag from an image.

Fortunatelly it is possible to workaround this problem so Docker Registry Cleaner will **safely** remove tag from image, without removing image itself.
The process is quite simple:

- find tags to remove
- upload fake image
- re-tag found tags to new image
- remove image with REST API call

Remove empty repositories
=========================

There is no way to remove repository using REST API, even one without tags - empty repo is still listed by registry.

Currently files should be cleaned on GC run on registry side (or some third party app, like this one).

---------------------
Example configuration
---------------------

Regex matching
==============

Removes build tags created by CI:


.. code:: yaml

   patterns:
     latest:
       - "latest"
     ci:
       "r-([0-9]+)": "\\1"
       "build-([0-9]+)": "\\1"
   
   repositories:
      some-name:
         paths:
           - "library/*"
         cleaners:
           latest:
             type: pattern
             pattern: ci
             max_items: 10

Remove unknown tags
===================

Removes tags that are not known for groups before it.

.. code:: yaml

   repositories:
     some-name:
       paths:
         - "library/*":
       cleaners:
         # ... other groups ...
         other:
           type: max
           max_items: 0


Semver tags
===========

As in http://semver.org/

.. code:: yaml

         versioned:
           type: semver
           max_items: 100
           groups:
             current_minor:
               where:
                 major: latest
                 minor: latest
               preserve:
                 patch: 6
             current_major:
               where:
                 major: latest
                 minor:
                   min: 0
                   max: latest - 1
               preserve:
                 patch: 1
             archival:
               where:
                 major:
                   max: latest - 1
               preserve:
                 minor: 1
                 patch: 1
               max_items: 20


Above config will:

- save only up to 100 newest versions
- save up to 6 versions with latest major & minor revisions
- save latest patch version for each minor release in latest major version (2.1.1, 2.2.10 but no 2.2.9)
- save latest minor & patch version for older major revisions

For more info see https://docker-registry-cleaner.readthedocs.io/en/latest/code/selectors.html#glorpen-docker-registry-cleaner-selectors-semver

-----
Usage
-----

App requires two paths:

- configuration file
- registry data, /var/lib/registry by default

It is advised to temporarly disable real registry (as when using normal ``registry garbage-collect``).

For example, to list repos:

.. code:: bash

   docker run --rm -v `pwd`:/srv glorpen/registry-cleaner /srv/config.yml -d /srv/registry-data list-repos

and then to clean:

.. code:: bash

   docker run --rm -v `pwd`:/srv glorpen/registry-cleaner /srv/config.yml -d /srv/registry-data clean``
