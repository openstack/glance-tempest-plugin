==============================
Tempest Integration for Glance
==============================

This directory contains additional Glance tempest tests.

See the tempest plugin docs for information on using it:
https://docs.openstack.org/tempest/latest/plugin.html#using-plugins

To run all tests from this plugin,
1. Clone  glance-tempest-plugin repo from github::

    $ git clone https://opendev.org/openstack/glance-tempest-plugin

2. Install the plugin::

    $ pip3 install -e glance-tempest-plugin

3. Confirm it's installed::

    $ tempest list-plugins

4. Create new file tempest.conf inside /etc/tempest directory and run with below
   content, including rbac enablement

::
     [identity]
     auth_version = v3
     uri_v3 = <Full URI of the OpenStack Identity API>

     [auth]
     use_dynamic_credentials = True
     admin_domain_name = Default
     admin_project_name = admin
     admin_password = admin
     admin_username = admin
     admin_system = True

     [image_feature_enabled]
     enforce_scope = True
     os_glance_reserved = True
     import_image = False

     [enforce_scope]
     glance = true



5. Then from the tempest directory run::

    $ tox -e all -- glance_tempest_plugin


It is expected that Glance third party CI's use the `all` tox environment
above for all test runs. Developers can also use this locally to perform more
extensive testing.

Any typical devstack instance should be able to run all Glance plugin tests.
For completeness, here is an example of a devstack local.conf that should
work. Update backend information to fit your environment.

::

    [[local|localrc]]
    ADMIN_PASSWORD=secret
    SERVICE_TOKEN=$ADMIN_PASSWORD
    MYSQL_PASSWORD=$ADMIN_PASSWORD
    RABBIT_PASSWORD=$ADMIN_PASSWORD
    SERVICE_PASSWORD=$ADMIN_PASSWORD
    LOGFILE=$DEST/logs/stack.sh.log
    LOGDAYS=2
    SYSLOG=False
    LOG_COLOR=False
    RECLONE=yes
    ENABLED_SERVICES=g-api,dstat,key
    ENABLED_SERVICES+=,mysql,tempest
