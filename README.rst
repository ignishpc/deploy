.. image:: https://raw.githubusercontent.com/ignishpc/docs/main/logos/svg/ignis-hpc.svg
   :width: 128
   :alt: IgnisHPC logo

===============
IgnisHPC Deploy
===============

Documentation: `IgnisHPC docs <https://ignishpc.readthedocs.io>`_


-------
Install
-------

You can install IgnisHPC using pip::

 $ pip install ignishpc

External requirements
^^^^^^^^^^^^^^^^^^^^^

 - Docker: IgnisHPC is run inside containers, so docker must be installed.
 - Git (optional): The git binary is required for building IgnisHPC images from repositories.

Usage
^^^^^

List services status::

$ ignis-deploy status

List available services::

 $ ignis-deploy -h

List available service actions::

 $ ignis-deploy <service> -h