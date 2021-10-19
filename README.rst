==============================
Tempest Integration for Glance
==============================

This directory contains additional Glance tempest tests.

See the tempest plugin docs for information on using it:
https://docs.openstack.org/tempest/latest/plugin.html#using-plugins

To run all tests from this plugin, install glance into your environment. Then
from the tempest directory run::

    $ tox -e all -- glance_tempest_plugin


It is expected that Glance third party CI's use the `all` tox environment
above for all test runs. Developers can also use this locally to perform more
extensive testing.
