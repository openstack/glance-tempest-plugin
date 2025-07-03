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


class ProjectAdminTests(rbac_base.MetadefV2RbacObjectsTest,
                        rbac_base.MetadefV2RbacObjectsTemplate):

    credentials = ['project_admin', 'project_alt_admin', 'primary']

    def test_get_object(self):
        ns_objects = self.create_objects()

        # Get all metadef objects with admin role
        for obj in ns_objects:
            resp = self.do_request(
                'show_namespace_object',
                expected_status=200,
                client=self.objects_client,
                namespace=obj['namespace']['namespace'],
                object_name=obj['object']['name'])
            self.assertEqual(obj['object']['name'], resp['name'])

    def test_list_objects(self):
        ns_objects = self.create_objects()

        # list all metadef objects with admin role
        for obj in ns_objects:
            self.assertObjectsList(obj, self.objects_client)

    def test_update_object(self):
        ns_objects = self.create_objects()

        # update all metadef objects with admin role of 'project'
        for obj in ns_objects:
            resp = self.do_request(
                'update_namespace_object',
                expected_status=200,
                namespace=obj['namespace']['namespace'],
                client=self.objects_client,
                object_name=obj['object']['name'],
                name=obj['object']['name'],
                description=data_utils.arbitrary_string(base_text="updated"))
            self.assertNotEqual(obj['object']['description'],
                                resp['description'])

    def test_delete_object(self):
        ns_objects = self.create_objects()
        # delete all metadef objects with admin role of 'project'
        for obj in ns_objects:
            self.do_request('delete_namespace_object',
                            expected_status=204,
                            namespace=obj['namespace']['namespace'],
                            object_name=obj['object']['name'],
                            client=self.objects_client)

            # Verify the object is deleted successfully
            self.do_request('show_namespace_object',
                            expected_status=exceptions.NotFound,
                            client=self.objects_client,
                            namespace=obj['namespace']['namespace'],
                            object_name=obj['object']['name'])

    def test_create_object(self):
        # As this is been covered in other tests for admin role,
        # skipping to test only create objects seperately.
        pass


class ProjectMemberTests(rbac_base.MetadefV2RbacObjectsTest,
                         rbac_base.MetadefV2RbacObjectsTemplate):

    credentials = ['project_member', 'project_alt_member', 'project_admin',
                   'project_alt_admin', 'primary']

    def test_create_object(self):
        namespaces = self.create_namespaces()

        # Make sure non admin role of 'project' forbidden to
        # create objects
        for namespace in namespaces:
            self.create_objects(namespace, self.project_id,
                                self.objects_client, is_admin=False)

    def test_get_object(self):
        ns_objects = self.create_objects()

        # Get object - member role from 'project' can access all
        # objects of it's own & only objects having public namespace of
        # 'alt_project'
        for obj in ns_objects:
            self.assertObjectGet(obj, self.project_id, self.objects_client)

    def test_list_objects(self):
        ns_objects = self.create_objects()

        # list objects - member role from 'project' can access all
        # objects of it's own & only objects having public namespace of
        # 'alt_project'
        for obj in ns_objects:
            self.assertObjectsList(obj, self.objects_client, self.project_id)

    def test_update_object(self):
        ns_objects = self.create_objects()

        # Make sure non admin role of 'project' not allowed to
        # update objects
        for obj in ns_objects:
            self.assertObjectUpdate(obj, self.project_id, self.objects_client)

    def test_delete_object(self):
        ns_objects = self.create_objects()

        # Make sure non admin role of 'project' not allowed to
        # delete objects
        for obj in ns_objects:
            self.assertObjectDelete(obj, self.project_id, self.objects_client)


class ProjectReaderTests(ProjectMemberTests):

    credentials = ['project_reader', 'project_alt_reader', 'project_admin',
                   'project_alt_admin', 'primary']
