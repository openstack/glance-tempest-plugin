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

import six

from tempest import config
from tempest.lib.common.utils import data_utils
from tempest.lib import decorators
from tempest.lib import exceptions

from glance_tempest_plugin.tests.rbac.v2 import base as rbac_base

CONF = config.CONF


class ImageProjectAdminTests(rbac_base.ImageV2RbacImageTest,
                             rbac_base.ImageV2RbacTemplate):

    credentials = ['project_admin', 'system_admin', 'project_alt_admin']

    @decorators.idempotent_id('025eea27-fa86-44a9-85a2-91295842f808')
    def test_create_image(self):
        image = self.do_request('create_image', expected_status=201,
                                **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        image = self.do_request('create_image', expected_status=201,
                                **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        image = self.do_request('create_image', expected_status=201,
                                **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        image = self.do_request('create_image', expected_status=201,
                                **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to create image.
            self.do_request('create_image',
                            expected_status=exceptions.Forbidden,
                            client=self.os_system_admin.image_client_v2,
                            **self.image(visibility='public'))

    @decorators.idempotent_id('61fd8b5e-8a0b-46ca-91c4-6c2c2d35039d')
    def test_get_image(self):
        # Ensure users can get private images owned by their project.
        project_id = self.persona.credentials.project_id
        project_member = self.setup_user_client(project_id=project_id)
        image = project_member.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image', image_id=image['id'])

        image = project_member.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image', image_id=image['id'])

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image', image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to get image.
            self.do_request('show_image', expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image', image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image', image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to get image.
            self.do_request('show_image', expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])
        project_id = self.persona.credentials.project_id
        self.admin_client.image_member_client_v2.create_image_member(
            image['id'], member=project_id)
        self.addCleanup(
            self.admin_client.image_member_client_v2.delete_image_member,
            image['id'], project_id)

        self.do_request('show_image', image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image', image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image', image_id=image['id'])

        self.do_request('show_image', expected_status=exceptions.NotFound,
                        image_id=data_utils.rand_uuid())

    @decorators.idempotent_id('d0c18f80-6168-4d98-a86e-c09d28d83bb0')
    def test_list_images(self):
        project_id = self.persona.credentials.project_id
        project_member = self.setup_user_client(project_id=project_id)
        project_client = self.setup_user_client()

        # Create a private image in the project
        private_image_in_project = project_member.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        private_image_in_project['id'])

        # Create a private image without an owner
        private_image_no_owner = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        private_image_no_owner['id'])

        # Create a private image in another project
        private_image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        private_image['id'])

        # Create a public image
        public_image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image,
                        public_image['id'])

        resp = self.do_request('list_images', expected_status=200)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to list images.
            self.do_request('list_images',
                            expected_status=exceptions.Forbidden,
                            client=self.os_system_admin.image_client_v2)
        image_ids = set(image['id'] for image in resp['images'])

        self.assertIn(private_image_no_owner['id'], image_ids)
        self.assertIn(private_image['id'], image_ids)
        self.assertIn(public_image['id'], image_ids)
        self.assertIn(private_image_in_project['id'], image_ids)

        # Create a shared image in another project
        shared_image_1 = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        shared_image_2 = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image,
                        shared_image_1['id'])
        self.addCleanup(self.admin_images_client.delete_image,
                        shared_image_2['id'])

        # Share the image from the other project with the user's project
        project_id = self.persona.credentials.project_id
        self.admin_client.image_member_client_v2.create_image_member(
            shared_image_1['id'], member=project_id)
        self.addCleanup(
            self.admin_client.image_member_client_v2.delete_image_member,
            shared_image_1['id'], project_id)

        # List images and assert the shared image is not in the list of images
        # because it hasn't been accepted, yet.
        resp = self.do_request('list_images', expected_status=200)
        image_ids = set(image['id'] for image in resp['images'])
        self.assertIn(shared_image_1['id'], image_ids)
        self.assertIn(shared_image_2['id'], image_ids)

        # Accept the image and ensure it's returned in the list of images
        project_member.image_member_client_v2.update_image_member(
            shared_image_1['id'], project_id, status='accepted')
        resp = self.do_request('list_images', expected_status=200)
        image_ids = set(image['id'] for image in resp['images'])
        self.assertIn(shared_image_1['id'], image_ids)
        self.assertIn(shared_image_2['id'], image_ids)

    @decorators.idempotent_id('9e9f7fd6-e93c-402c-9f3c-177fede8f645')
    def test_update_image(self):
        image = self.client.create_image(**self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=200,
                        image_id=image['id'], patch=patch_body)

        image = self.client.create_image(**self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=200,
                        image_id=image['id'], patch=patch_body)

        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=200,
                        image_id=image['id'], patch=patch_body)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to update image.
            self.do_request('update_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'], patch=patch_body)
        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=200,
                        image_id=image['id'], patch=patch_body)

        image = self.client.create_image(**self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=200,
                        image_id=image['id'], patch=patch_body)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=200,
                        image_id=image['id'], patch=patch_body)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to update image.
            self.do_request('update_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'], patch=patch_body)
        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=200,
                        image_id=image['id'], patch=patch_body)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to update image.
            self.do_request('update_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'], patch=patch_body)
        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=200,
                        image_id=image['id'], patch=patch_body)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to update image.
            self.do_request('update_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'], patch=patch_body)

    @decorators.idempotent_id('947f1ae1-c5b6-4552-89e3-1078ca722be4')
    def test_upload_image(self):
        file_contents = data_utils.random_bytes()
        image_data = six.BytesIO(file_contents)

        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)

        # upload file for private image - pass
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file', expected_status=204,
                        image_id=image['id'], data=image_data)

        # upload file for shared image - pass
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file', expected_status=204,
                        image_id=image['id'], data=image_data)

        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file', image_id=image['id'],
                        expected_status=204, data=image_data)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to store image file.
            self.do_request('store_image_file',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'], data=image_data)

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file', expected_status=204,
                        image_id=image['id'], data=image_data)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to store image file.
            self.do_request('store_image_file',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'], data=image_data)
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file', expected_status=204,
                        image_id=image['id'], data=image_data)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to store image file.
            self.do_request('store_image_file',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'], data=image_data)
        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file', expected_status=204,
                        image_id=image['id'], data=image_data)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to store image file.
            self.do_request('store_image_file',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'], data=image_data)
        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file', expected_status=204,
                        image_id=image['id'], data=image_data)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to store image file.
            self.do_request('store_image_file',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'], data=image_data)

    @decorators.idempotent_id('24891c04-28ca-41f9-92d1-c06d8ba4b83d')
    def test_download_image(self):
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('show_image_file', expected_status=204,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('show_image_file', expected_status=204,
                        image_id=image['id'])

        project_client = self.setup_user_client()

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('show_image_file', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to show image file.
            self.do_request('show_image_file',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('show_image_file', expected_status=204,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image_file', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to show image file.
            self.do_request('show_image_file',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image_file', expected_status=204,
                        image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image_file', expected_status=204,
                        image_id=image['id'])

    @decorators.idempotent_id('e45899d6-7e16-4cbf-b800-31c05e6caf8c')
    def test_delete_image(self):

        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to delete image.
            self.do_request('delete_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to delete image.
            self.do_request('delete_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.client.create_image(
            **self.image(visibility='private'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to delete image.
            self.do_request('delete_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.client.create_image(
            **self.image(visibility='shared'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='community'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to delete image.
            self.do_request('delete_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.client.create_image(
            **self.image(visibility='community'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to delete image.
            self.do_request('delete_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

    @decorators.idempotent_id('ec3da4dc-f478-4a70-8799-db0814e340f4')
    def test_add_image_member(self):
        # Create a user with the member role in a separate project.
        other_project_member_client = self.setup_user_client()
        other_project_id = other_project_member_client.credentials.project_id

        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        # Make sure the persona user can add image members to images they
        # create.
        self.do_request('create_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member=other_project_id)

    @decorators.idempotent_id('8719285b-5b7b-48b8-ba5e-2bc7e3535025')
    def test_get_image_member(self):
        # Create a user with the member role in a separate project.
        project_one_client = self.setup_user_client()
        project_one_id = project_one_client.credentials.project_id

        # Create an image and share it with the other project.
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=project_one_id)
        self.do_request('show_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member_id=project_one_id)

        # Create an image associated to a separate project and make project_one
        # a member.
        project_two_client = self.setup_user_client()
        image = project_two_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_two_client.image_member_client_v2.create_image_member(
            image['id'], member=project_one_id)
        self.do_request('show_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member_id=project_one_id)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to show image member.
            self.do_request('show_image_member',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_member_client_v2,
                            image_id=image['id'], member_id=project_one_id)

    @decorators.idempotent_id('daaef0c5-1172-457b-b1a3-0736b64c8426')
    def test_list_image_members(self):
        # Stash the project_id for this persona
        project_id = self.persona.credentials.project_id

        other_member_client = self.setup_user_client()
        other_member_project_id = other_member_client.credentials.project_id

        # Create an image as another user in a separate project and share that
        # image with this user and the other member.
        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        for p_id in [project_id, other_member_project_id]:
            project_client.image_member_client_v2.create_image_member(
                image['id'], member=p_id)
        resp = self.do_request('list_image_members',
                               client=self.persona.image_member_client_v2,
                               expected_status=200, image_id=image['id'])
        members = set(m['member_id'] for m in resp['members'])
        self.assertIn(project_id, members)
        self.assertIn(other_member_project_id, members)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to list image members.
            self.do_request('list_image_members',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_member_client_v2,
                            image_id=image['id'])

    @decorators.idempotent_id('2baaaca0-6335-4219-9bd9-207a5cfda6a2')
    def test_update_image_member(self):
        project_client = self.setup_user_client()
        # Create a shared image in a separate project and share the with the
        # persona project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=self.persona.credentials.project_id)

        # Make sure the persona user can accept the image.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member_id=self.persona.credentials.project_id,
                        status='accepted')

        # Make sure the persona user can reject the image.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member_id=self.persona.credentials.project_id,
                        status='rejected')

        # Create another shared image in a separate project (not the persona
        # user's project).
        member_client = self.setup_user_client()
        member_project_id = member_client.credentials.project_id
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        # Share the image with another project.
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)

        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member_id=member_project_id, status='accepted')

        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member_id=member_project_id, status='rejected')
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to update image member.
            self.do_request('update_image_member',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_member_client_v2,
                            image_id=image['id'], member_id=member_project_id,
                            status='rejected')

    @decorators.idempotent_id('7f0a8e2b-b655-416a-914b-9615cff18bbf')
    def test_delete_image_member(self):
        # Create a user with authorization on another project.
        member_client = self.setup_user_client()
        member_project_id = member_client.credentials.project_id

        # Create a separate user with authorization on the persona project.
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)

        # Create an image in the persona project and share it with the member.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)

        # Make sure we, as the image owners, can remove membership to that
        # image.
        self.do_request('delete_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=204,
                        image_id=image['id'], member_id=member_project_id)

        # Create a new user with authorization on a separate project.
        project_client = self.setup_user_client()

        # Create an image in that project and share it with the member project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)

        self.do_request('delete_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=204, image_id=image['id'],
                        member_id=member_project_id)
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to delete image member.
            self.do_request('delete_image_member',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_member_client_v2,
                            image_id=image['id'], member_id=member_project_id)

    @decorators.idempotent_id('dfc73f6f-bf91-4b6a-8482-acc8c436e066')
    def test_deactivate_image(self):
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        file_contents = data_utils.random_bytes()
        image_data = six.BytesIO(file_contents)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        self.do_request('deactivate_image', expected_status=204,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        self.do_request('deactivate_image', expected_status=204,
                        image_id=image['id'])

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        self.do_request('deactivate_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to deactivate image.
            self.do_request('deactivate_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        self.do_request('deactivate_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to deactivate image.
            self.do_request('deactivate_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.do_request('deactivate_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to deactivate image.
            self.do_request('deactivate_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.do_request('deactivate_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to deactivate image.
            self.do_request('deactivate_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

    @decorators.idempotent_id('3cbef53c-ab8a-4343-b993-8f9e14ab90d1')
    def test_reactivate_image(self):
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        file_contents = data_utils.random_bytes()
        image_data = six.BytesIO(file_contents)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])
        self.do_request('reactivate_image', expected_status=204,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])
        self.do_request('reactivate_image', expected_status=204,
                        image_id=image['id'])

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])
        self.do_request('reactivate_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to reactivate image.
            self.do_request('reactivate_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])
        self.do_request('reactivate_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to reactivate image.
            self.do_request('reactivate_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.admin_images_client.deactivate_image(image['id'])
        self.do_request('reactivate_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to reactivate image.
            self.do_request('reactivate_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.admin_images_client.deactivate_image(image['id'])
        self.do_request('reactivate_image', expected_status=204,
                        image_id=image['id'])
        if not CONF.glance_api.system_scope_supported:
            # Check that system user is not permitted to reactivate image.
            self.do_request('reactivate_image',
                            expected_status=exceptions.NotFound,
                            client=self.os_system_admin.image_client_v2,
                            image_id=image['id'])


class NamespacesProjectAdminTests(rbac_base.MetadefV2RbacNamespaceTest,
                                  rbac_base.MetadefV2RbacNamespaceTemplate):

    credentials = ['project_admin', 'project_alt_admin', 'primary']

    def test_list_namespaces(self):
        actual_namespaces = self.create_namespaces()

        # Get above created namespace by admin role
        resp = self.do_request('list_namespaces', expected_status=200,
                               client=self.admin_namespace_client)

        self.assertListNamespaces(actual_namespaces, resp)

    def test_get_namespace(self):
        actual_namespaces = self.create_namespaces()

        # Get above created namespace by admin role
        for ns in actual_namespaces:
            resp = self.do_request('show_namespace', expected_status=200,
                                   namespace=ns['namespace'],
                                   client=self.admin_namespace_client)
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
                client=self.admin_namespace_client,
                description=data_utils.arbitrary_string(base_text="updated"))
            self.assertNotEqual(ns['description'], resp['description'])

    def test_delete_namespace(self):
        actual_namespaces = self.create_namespaces()

        # Deleting the above created namespace by admin role
        for ns in actual_namespaces:
            self.do_request('delete_namespace', expected_status=204,
                            namespace=ns['namespace'],
                            client=self.admin_namespace_client,)

            # Verify the namespaces are deleted successfully
            self.do_request('show_namespace',
                            expected_status=exceptions.NotFound,
                            namespace=ns['namespace'],
                            client=self.admin_namespace_client,)


class RSTypesProjectAdminTests(rbac_base.MetadefV2RbacResourceTypeTest,
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


class ObjectsProjectAdminTests(rbac_base.MetadefV2RbacObjectsTest,
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


class PropertiesProjectAdminTests(rbac_base.MetadefV2RbacPropertiesTest,
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


class TagsProjectAdminTests(rbac_base.MetadefV2RbacTagsTest,
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

        def assertDeleteTags(tag, client, multiple_tags=False):
            namespace = tag['namespace']['namespace']
            if multiple_tags:
                self.do_request('delete_namespace_tags',
                                expected_status=204,
                                namespace=namespace,
                                client=client)
                # Verify the tags are deleted successfully
                resp = self.do_request('list_namespace_tags',
                                       client=client,
                                       namespace=namespace)
                self.assertEqual(0, len(resp['tags']))
            else:
                tag_name = tag['tag']['name']
                self.do_request('delete_namespace_tag',
                                expected_status=204,
                                namespace=namespace,
                                tag_name=tag_name,
                                client=client)

                # Verify the tag is deleted successfully
                self.do_request('show_namespace_tag',
                                expected_status=exceptions.NotFound,
                                client=client,
                                namespace=namespace,
                                tag_name=tag_name)

        # delete all metadef tags with admin role of 'project'
        for tag in ns_tags:
            assertDeleteTags(tag, self.tags_client)

        # Create multiple tags
        ns_multiple_tags = self.create_tags(namespaces, multiple_tags=True)
        # delete all metadef multiple tags with admin role of 'project'
        for tags in ns_multiple_tags:
            assertDeleteTags(tags, self.tags_client, multiple_tags=True)
