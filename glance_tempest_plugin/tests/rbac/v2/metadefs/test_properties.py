# Copyright 2021 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from tempest.lib import exceptions

from glance_tempest_plugin.tests.rbac.v2 import base as rbac_base


class ProjectAdminTests(rbac_base.MetadefV2RbacPropertiesTest,
                        rbac_base.MetadefV2RbacPropertiesTemplate):

    credentials = ['project_admin', 'project_alt_admin', 'primary']

    def test_create_property(self):
        # As this is been covered in other tests for admin role,
        # skipping to test only create properties separately.
        pass

    def test_get_properties(self):
        ns_properties = self.create_properties()

        # Get all metadef properties with admin role of 'project'
        for prop in ns_properties:
            resp = self.do_request(
                'show_namespace_properties',
                expected_status=200,
                client=self.properties_client,
                namespace=prop['namespace']['namespace'],
                property_name=prop['property']['name'])
            self.assertEqual(prop['property'], resp)

    def test_list_properties(self):
        ns_properties = self.create_properties()
        # list all metadef properties with admin role of 'project'
        for prop in ns_properties:
            self.assertPropertyList(prop, self.properties_client)

    def test_update_properties(self):
        ns_properties = self.create_properties()

        # update all metadef properties with admin role of 'project'
        for prop in ns_properties:
            resp = self.do_request(
                'update_namespace_properties',
                expected_status=200,
                namespace=prop['namespace']['namespace'],
                client=self.properties_client,
                title="UPDATE_Property",
                property_name=prop['property']['name'],
                name=prop['property']['name'],
                type="string")
            self.assertNotEqual(prop['property']['title'],
                                resp['title'])

    def test_delete_properties(self):
        ns_properties = self.create_properties()

        # delete all metadef properties with admin role of 'project'
        for prop in ns_properties:
            self.do_request('delete_namespace_property',
                            expected_status=204,
                            namespace=prop['namespace']['namespace'],
                            property_name=prop['property']['name'],
                            client=self.properties_client)

            # Verify the property is deleted successfully
            self.do_request('show_namespace_properties',
                            expected_status=exceptions.NotFound,
                            client=self.properties_client,
                            namespace=prop['namespace']['namespace'],
                            property_name=prop['property']['name'])


class ProjectMemberTests(rbac_base.MetadefV2RbacPropertiesTest,
                         rbac_base.MetadefV2RbacPropertiesTemplate):

    credentials = ['project_member', 'project_alt_member',
                   'project_admin', 'project_alt_admin', 'primary']

    def test_create_property(self):
        namespaces = self.create_namespaces()

        # Make sure non admin role of 'project' forbidden to
        # create properties
        for namespace in namespaces:
            self.create_properties(namespace, self.project_id,
                                   self.properties_client, is_admin=False)

    def test_get_properties(self):
        ns_properties = self.create_properties()

        # Get property - member role from 'project' can access all
        # properties of it's own & only propertys having public namespace of
        # 'alt_project'
        for prop in ns_properties:
            self.assertPropertyGet(prop, self.properties_client,
                                   self.project_id)

    def test_list_properties(self):
        ns_properties = self.create_properties()

        # list properties - member role from 'project' can access all
        # properties of it's own & only propertys having public namespace of
        # 'alt_project'
        for prop in ns_properties:
            self.assertPropertyList(prop, self.properties_client,
                                    self.project_id)

    def test_update_properties(self):
        ns_properties = self.create_properties()

        # Make sure non admin role of 'project' not allowed to
        # update properties
        for prop in ns_properties:
            self.assertPropertyUpdate(prop, self.properties_client,
                                      self.project_id)

    def test_delete_properties(self):
        ns_properties = self.create_properties()

        # Make sure non admin role of 'project' not allowed to
        # delete properties
        for prop in ns_properties:
            self.assertPropertyDelete(prop, self.properties_client,
                                      self.project_id)


class ProjectReaderTests(ProjectMemberTests):

    credentials = ['project_reader', 'project_alt_reader',
                   'project_admin', 'project_alt_admin', 'primary']
