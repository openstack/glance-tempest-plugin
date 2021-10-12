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

from glance_tempest_plugin.tests.rbac.v2 import base as rbac_base


class ProjectAdminTests(rbac_base.MetadefV2RbacTagsTest,
                        rbac_base.MetadefV2RbacTagsTemplate):

    credentials = ['project_admin', 'project_alt_admin', 'primary']

    def test_create_tag(self):
        # As this is been covered in other tests for admin role,
        # skipping to test only create properties separately.
        pass

    def test_get_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)

        # Get all metadef tags with admin role of 'project'
        for tag in ns_tags:
            resp = self.do_request(
                'show_namespace_tag',
                expected_status=200,
                client=self.tags_client,
                namespace=tag['namespace']['namespace'],
                tag_name=tag['tag']['name'])
            self.assertEqual(tag['tag']['name'], resp['name'])

    def test_list_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)
        # list all metadef tags with admin role of 'project'
        for tag in ns_tags:
            self.assertTagsList(tag, self.tags_client)

    def test_update_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)

        # update all metadef tags with admin role of 'project'
        for tag in ns_tags:
            resp = self.do_request(
                'update_namespace_tag',
                expected_status=200,
                namespace=tag['namespace']['namespace'],
                client=self.tags_client,
                tag_name=tag['tag']['name'],
                name=data_utils.arbitrary_string(base_text="updated-name"))
            self.assertNotEqual(tag['tag']['name'], resp['name'])

    def test_delete_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)

        # delete all metadef tags with admin role of 'project'
        for tag in ns_tags:
            self.assertDeleteTags(tag, self.tags_client)

        # Create multiple tags
        ns_multiple_tags = self.create_tags(namespaces, multiple_tags=True)
        # delete all metadef multiple tags with admin role of 'project'
        for tags in ns_multiple_tags:
            self.assertDeleteTags(tags, self.tags_client, multiple_tags=True)


class ProjectMemberTests(rbac_base.MetadefV2RbacTagsTest,
                         rbac_base.MetadefV2RbacTagsTemplate):

    credentials = ['project_member', 'project_alt_member',
                   'project_admin', 'project_alt_admin', 'primary']

    def test_create_tag(self):
        namespaces = self.create_namespaces()

        # Make sure non admin role of 'project' forbidden to
        # create tags
        for namespace in namespaces:
            self.create_tags(namespace, self.tags_client, self.project_id,
                             is_admin=False)

            # Create Multiple Tags
            self.create_tags(namespace, self.tags_client, self.project_id,
                             multiple_tags=True, is_admin=False)

    def test_get_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)

        # Get tag - member role from 'project' can access all
        # tags of it's own & only tags having public namespace of
        # 'alt_project'
        for tag in ns_tags:
            self.assertTagGet(tag, self.tags_client, self.project_id)

    def test_list_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)

        # list tags - member role from 'project' can access all
        # tags of it's own & only tags having public namespace of
        # 'alt_project'
        for tag in ns_tags:
            self.assertTagsList(tag, self.tags_client, self.project_id)

    def test_update_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)

        # Make sure non admin role of 'project' not allowed to
        # update tags
        for tag in ns_tags:
            self.assertTagUpdate(tag, self.tags_client, self.project_id)

    def test_delete_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)

        # Make sure non admin role of 'project' not allowed to
        # delete tags
        for tag in ns_tags:
            self.assertDeleteTags(tag, self.tags_client, self.project_id,
                                  is_admin=False)

        # Create Multiple Tags
        ns_multiple_tags = self.create_tags(namespaces, multiple_tags=True)
        # Make sure non admin role of 'project' not allowed to
        # delete multiple tags
        for tags in ns_multiple_tags:
            self.assertDeleteTags(tags, self.tags_client, self.project_id,
                                  multiple_tags=True, is_admin=False)


class ProjectReaderTests(ProjectMemberTests):

    credentials = ['project_reader', 'project_alt_reader',
                   'project_admin', 'project_alt_admin', 'primary']
