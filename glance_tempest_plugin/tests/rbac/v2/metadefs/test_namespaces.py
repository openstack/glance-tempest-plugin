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

from tempest.lib.common.utils import data_utils
from tempest.lib import exceptions

from glance_tempest_plugin.tests.rbac.v2 import base as rbac_base


class ProjectAdminTests(rbac_base.MetadefV2RbacNamespaceTest,
                        rbac_base.MetadefV2RbacNamespaceTemplate):

    credentials = ['project_admin', 'project_alt_admin', 'primary']

    def test_list_namespaces(self):
        actual_namespaces = self.create_namespaces()

        # Get above created namespace by admin role
        resp = self.do_request('list_namespaces', expected_status=200,
                               client=self.namespaces_client)

        self.assertListNamespaces(actual_namespaces, resp)

    def test_get_namespace(self):
        actual_namespaces = self.create_namespaces()

        # Get above created namespace by admin role
        for ns in actual_namespaces:
            resp = self.do_request('show_namespace', expected_status=200,
                                   namespace=ns['namespace'],
                                   client=self.namespaces_client)
            self.assertEqual(ns['namespace'], resp['namespace'])

    def test_create_namespace(self):
        # As this is been covered in other tests for admin role,
        # skipping to test only create namespaces seperately.
        pass

    def test_update_namespace(self):
        actual_namespaces = self.create_namespaces()

        # Updating the above created namespace by admin role
        for ns in actual_namespaces:
            resp = self.do_request(
                'update_namespace', expected_status=200,
                namespace=ns['namespace'],
                client=self.namespaces_client,
                description=data_utils.arbitrary_string(base_text="updated"))
            self.assertNotEqual(ns['description'], resp['description'])

    def test_delete_namespace(self):
        actual_namespaces = self.create_namespaces()

        # Deleting the above created namespace by admin role
        for ns in actual_namespaces:
            self.do_request('delete_namespace', expected_status=204,
                            namespace=ns['namespace'],
                            client=self.namespaces_client,)

            # Verify the namespaces are deleted successfully
            self.do_request('show_namespace',
                            expected_status=exceptions.NotFound,
                            namespace=ns['namespace'],
                            client=self.admin_namespace_client,)


class ProjectMemberTests(rbac_base.MetadefV2RbacNamespaceTest,
                         rbac_base.MetadefV2RbacNamespaceTemplate):

    credentials = ['project_member', 'project_alt_member',
                   'project_admin', 'project_alt_admin', 'primary']

    def test_get_namespace(self):

        actual_namespaces = self.create_namespaces()

        # Get namespace - member role from 'project' can access all
        # namespaces of it's own & only public namespace of 'alt_project'
        for actual_ns in actual_namespaces:
            self.assertGetNamespace(actual_ns, self.project_id,
                                    self.namespaces_client)

    def test_list_namespaces(self):
        actual_namespaces = self.create_namespaces()

        # List namespace - member role from 'project' can access all
        # namespaces of it's own & only public namespace of 'alt_project'
        resp = self.do_request('list_namespaces',
                               client=self.namespaces_client,
                               expected_status=200)
        self.assertListNamespaces(actual_namespaces, resp, self.project_id)

    def test_update_namespace(self):
        actual_namespaces = self.create_namespaces()

        # Check member role of 'project' is forbidden to update namespace
        for actual_ns in actual_namespaces:
            self.assertUpdateNamespace(actual_ns, self.project_id,
                                       self.namespaces_client)

    def test_create_namespace(self):
        # Check non-admin role of 'project' not allowed to create namespace
        self.do_request('create_namespace',
                        expected_status=exceptions.Forbidden,
                        client=self.namespaces_client,
                        namespace=data_utils.arbitrary_string())

    def test_delete_namespace(self):
        actual_namespaces = self.create_namespaces()

        # Check member role of 'project' is forbidden to delete namespace
        for actual_ns in actual_namespaces:
            self.assertDeleteNamespace(actual_ns, self.project_id,
                                       self.namespaces_client)

        # Verify the namespaces are not deleted
        for actual_ns in actual_namespaces:
            self.do_request('show_namespace',
                            expected_status=200,
                            client=self.admin_namespace_client,
                            namespace=actual_ns['namespace'])


class ProjectReaderTests(ProjectMemberTests):
    credentials = ['project_reader', 'project_alt_reader',
                   'project_admin', 'project_alt_admin', 'primary']
