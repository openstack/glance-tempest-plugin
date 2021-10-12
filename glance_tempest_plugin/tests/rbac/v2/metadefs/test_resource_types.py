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

from glance_tempest_plugin.tests.rbac.v2 import base as rbac_base


class ProjectAdminTests(rbac_base.MetadefV2RbacResourceTypeTest,
                        rbac_base.MetadefV2RbacResourceTypeTemplate):

    credentials = ['project_admin', 'project_alt_admin', 'primary']

    def test_create_resource_type(self):
        # As this is been covered in other tests for admin role,
        # skipping to test only create resource types separately.
        pass

    def test_get_resource_type(self):
        ns_rs_types = self.create_resource_types()

        # Get all metadef resource types with admin role of 'project'
        for rs_type in ns_rs_types:
            resp = self.do_request(
                'list_resource_type_association',
                expected_status=200,
                client=self.resource_types_client,
                namespace_id=rs_type['namespace']['namespace'])
            self.assertEqual(rs_type['resource_type']['name'],
                             resp['resource_type_associations'][0]['name'])

    def test_list_resource_types(self):
        ns_rs_types = self.create_resource_types()

        # list resource types - with admin role of 'project'
        resp = self.do_request('list_resource_types',
                               expected_status=200,
                               client=self.resource_types_client)

        # Verify that admin role of 'project' will be able to view available
        # resource types
        self.assertRSTypeList(ns_rs_types, resp)

    def test_delete_resource_type(self):
        ns_rs_types = self.create_resource_types()

        # delete all metadef resource types with admin role of 'project'
        for rs_type in ns_rs_types:
            self.do_request('delete_resource_type_association',
                            expected_status=204,
                            namespace_id=rs_type['namespace']['namespace'],
                            resource_name=rs_type['resource_type']['name'],
                            client=self.resource_types_client)

            # Verify the resource types is deleted successfully
            resp = self.do_request(
                'list_resource_type_association', expected_status=200,
                client=self.resource_types_client,
                namespace_id=rs_type['namespace']['namespace'])
            self.assertEqual([], resp['resource_type_associations'])


class ProjectMemberTests(rbac_base.MetadefV2RbacResourceTypeTest,
                         rbac_base.MetadefV2RbacResourceTypeTemplate):

    credentials = ['project_member', 'project_alt_member', 'project_admin',
                   'project_alt_admin', 'primary']

    def test_create_resource_type(self):
        namespaces = self.create_namespaces()

        # Make sure non admin role of 'project' forbidden to
        # create resource types
        for namespace in namespaces:
            self.create_resource_types(namespace, self.project_id,
                                       self.resource_types_client,
                                       is_admin=False)

    def test_get_resource_type(self):
        ns_rs_types = self.create_resource_types()

        # Get resource type - member role from 'project' can access all
        # resource types of it's own & only resource types having public
        # namespace of 'alt_project'
        for rs_type in ns_rs_types:
            self.assertRSTypeGet(rs_type, self.resource_types_client,
                                 self.project_id)

    def test_list_resource_types(self):
        ns_rs_types = self.create_resource_types()

        # list resource types - with member role of 'project'
        resp = self.do_request('list_resource_types',
                               expected_status=200,
                               client=self.resource_types_client)

        # Verify that member role of 'project' will be able to view available
        # resource types
        self.assertRSTypeList(ns_rs_types, resp)

        # list resource types -  with member role of 'alt_project'
        resp = self.do_request('list_resource_types',
                               expected_status=200,
                               client=self.resource_types_client)

    def test_delete_resource_type(self):
        ns_rs_types = self.create_resource_types()

        # Make sure non admin role of 'project' not allowed to
        # delete resource types
        for rs_type in ns_rs_types:
            self.assertRSTypeDelete(rs_type, self.resource_types_client,
                                    self.project_id)


class ProjectReaderTests(ProjectMemberTests):

    credentials = ['project_reader', 'project_alt_reader', 'project_admin',
                   'project_alt_admin', 'primary']
