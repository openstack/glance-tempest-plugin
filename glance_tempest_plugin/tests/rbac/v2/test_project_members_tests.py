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


class ImagesProjectMemberTests(rbac_base.ImageV2RbacImageTest,
                               rbac_base.ImageV2RbacTemplate):

    credentials = ['project_member', 'project_admin', 'system_admin',
                   'admin', 'project_alt_admin', 'project_alt_member']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.alt_project_images_client = (
            cls.os_project_alt_member.image_client_v2)

    @decorators.idempotent_id('a71e7caf-2403-4fed-a4bf-9717949ecde2')
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

        self.do_request('create_image', expected_status=exceptions.Forbidden,
                        **self.image(visibility='public'))

    @decorators.idempotent_id('2adf7202-7fc9-4a6e-b6dd-fb3d40365ccb')
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
        self.do_request('show_image', expected_status=exceptions.NotFound,
                        image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image', expected_status=exceptions.NotFound,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image', expected_status=exceptions.NotFound,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

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

    @decorators.idempotent_id('259d5578-410e-4b0f-bb2d-cb5b057bc696')
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
        private_image_no_owner = self.os_admin.image_client_v2.create_image(
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
        image_ids = set(image['id'] for image in resp['images'])

        self.assertNotIn(private_image_no_owner['id'], image_ids)
        self.assertNotIn(private_image['id'], image_ids)
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
        self.assertNotIn(shared_image_1['id'], image_ids)
        self.assertNotIn(shared_image_2['id'], image_ids)

        # Accept the image and ensure it's returned in the list of images
        project_member.image_member_client_v2.update_image_member(
            shared_image_1['id'], project_id, status='accepted')
        resp = self.do_request('list_images', expected_status=200)
        image_ids = set(image['id'] for image in resp['images'])
        self.assertIn(shared_image_1['id'], image_ids)
        self.assertNotIn(shared_image_2['id'], image_ids)

    @decorators.idempotent_id('13f8949b-3419-4a4a-bd0b-71fa711206fd')
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
        self.do_request('update_image', expected_status=exceptions.NotFound,
                        image_id=image['id'], patch=patch_body,
                        client=self.alt_project_images_client)

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=exceptions.NotFound,
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
        self.do_request('update_image', expected_status=exceptions.NotFound,
                        image_id=image['id'], patch=patch_body)

        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'], patch=patch_body,
                        client=self.alt_project_images_client)

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'], patch=patch_body,
                        client=self.alt_project_images_client)

    @decorators.idempotent_id('bd5845dc-d96b-4d83-a8da-7978bd91ddc1')
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
        self.do_request('store_image_file',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], data=image_data,
                        client=self.alt_project_images_client)

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], data=image_data)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], data=image_data)

        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'], data=image_data,
                        client=self.alt_project_images_client)

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'], data=image_data,
                        client=self.alt_project_images_client)

    @decorators.idempotent_id('3dfa6f70-f6fe-4ed5-96eb-5f4634064aa3')
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
        self.do_request('show_image_file', expected_status=exceptions.NotFound,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('show_image_file', expected_status=exceptions.NotFound,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image_file', expected_status=exceptions.NotFound,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

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

    @decorators.idempotent_id('326d267a-de9d-4217-aadc-a0f2b5993537')
    def test_delete_image(self):

        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.do_request('delete_image', expected_status=exceptions.NotFound,
                        image_id=image['id'],
                        client=self.alt_project_images_client)
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.do_request('delete_image', expected_status=exceptions.NotFound,
                        image_id=image['id'])
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        image = self.client.create_image(
            **self.image(visibility='private'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.do_request('delete_image', expected_status=exceptions.NotFound,
                        image_id=image['id'])
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        project_id = self.persona.credentials.project_id
        project_member = self.setup_user_client(project_id=project_id)
        image = project_member.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='community'))
        self.do_request('delete_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'])
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        image = self.client.create_image(
            **self.image(visibility='community'))
        self.do_request('delete_image', expected_status=204,
                        image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.do_request('delete_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'],
                        client=self.alt_project_images_client)
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

    @decorators.idempotent_id('395579c9-92bb-40a9-a8b6-9daaa20ae610')
    def test_add_image_member(self):
        member_client = self.setup_user_client()
        member_project_id = member_client.credentials.project_id
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])

        # As users with authorization on the project that owns the image, we
        # should be able to share that image with other projects.
        self.do_request('create_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member=member_project_id)

    @decorators.idempotent_id('67510e3f-57cd-4a76-9e96-577e49229677')
    def test_get_image_member(self):
        member_client = self.setup_user_client()
        member_project_id = member_client.credentials.project_id
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)
        self.do_request('show_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member_id=member_project_id)

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)
        # The user can't show the members for this image because they can't get
        # the image or pass the get_image policy, which is processed before
        # fetching the members.
        self.do_request('show_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], member_id=member_project_id)

    @decorators.idempotent_id('64ec16c4-3b8d-464d-88fb-f274241b1302')
    def test_list_image_members(self):
        # Stash the project_id for this persona.
        project_id = self.persona.credentials.project_id

        other_member_client = self.setup_user_client()
        other_member_project_id = other_member_client.credentials.project_id

        # Create an image as an other user in a separate project and share that
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
        # Make sure this user (persona) can't view members of an image other
        # than themselves.
        self.assertIn(project_id, members)
        self.assertNotIn(other_member_project_id, members)

    @decorators.idempotent_id('12636be0-6188-4003-8824-de4f89e3c745')
    def test_update_image_member(self):
        # Create a new user with authorization on another project.
        other_project_client = self.setup_user_client()

        # Create a shared image in the other project and share the image with
        # the persona user's project.
        image = other_project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        other_project_client.image_member_client_v2.create_image_member(
            image['id'], member=self.persona.credentials.project_id)

        # Make sure the persona users can accept the image.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member_id=self.persona.credentials.project_id,
                        status='accepted')

        # Make sure the persona users can reject the image.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=200, image_id=image['id'],
                        member_id=self.persona.credentials.project_id,
                        status='rejected')

        # Create a new user with authorization on another project to act as a
        # different member.
        member_client = self.setup_user_client()
        member_project_id = member_client.credentials.project_id

        # Create another image with the first project_client to share with the
        # new member user.
        image = other_project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        other_project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)

        # Make sure the persona user can't accept images for other projects
        # they are not a member of.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], member_id=member_project_id,
                        status='accepted')

        # Make sure the persona user can't reject images for other projects
        # they are not a member of.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], member_id=member_project_id,
                        status='rejected')

    @decorators.idempotent_id('bcfda1fa-ea65-47ce-8434-a64d85512fcf')
    def test_delete_image_member(self):
        # Create a new user with authorization on a separate project.
        member_client = self.setup_user_client()
        member_project_id = member_client.credentials.project_id

        # Create an image in the persona user's project and share that image
        # with the new member user.
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)

        # Make sure the persona user can delete image members from images they
        # own.
        self.do_request('delete_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=204,
                        image_id=image['id'], member_id=member_project_id)

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)

        # Make sure the persona user can't delete image members from images
        # outside their project.
        self.do_request('delete_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], member_id=member_project_id)

    @decorators.idempotent_id('abf9fe8b-ada3-4509-b15b-76d04e58f4e8')
    def test_deactivate_image(self):
        # Create a new user with authorization on the persona user's project.
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        file_contents = data_utils.random_bytes()
        image_data = six.BytesIO(file_contents)

        # Create a private image in the persona user's project and make sure
        # the persona user can deactivate it.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        self.do_request('deactivate_image', expected_status=204,
                        image_id=image['id'])
        resp = self.client.show_image(image_id=image['id'])
        self.assertTrue(resp['status'] == 'deactivated')

        # Create a shared image in the persona user's project and make sure the
        # persona user can deactivate it.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        self.do_request('deactivate_image', expected_status=204,
                        image_id=image['id'])
        resp = self.client.show_image(image_id=image['id'])
        self.assertTrue(resp['status'] == 'deactivated')

        # Create a new user with authorization on a separate project.
        project_client = self.setup_user_client()

        # Create a private image in that new project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        # The user can't deactivate this image because they can't find it.
        self.do_request('deactivate_image',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'])

        # Create a shared image in the new project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        # The user can't deactivate this image because they can't find it.
        self.do_request('deactivate_image',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

        # Project users can't deactivate community images, only administrators
        # should be able to do this.
        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.do_request('deactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

        # Project users can't deactivate public images, only administrators
        # should be able to do this.
        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.do_request('deactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

    @decorators.idempotent_id('58558447-8618-4dbe-97ce-bfc39b3743e7')
    def test_reactivate_image(self):
        # Create a new user with authorization on the persona user's project.
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        file_contents = data_utils.random_bytes()
        image_data = six.BytesIO(file_contents)

        # Create a private image within the persona user's project and make
        # sure we can reactivate it.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])
        resp = self.client.show_image(image_id=image['id'])
        self.assertTrue(resp['status'] == 'deactivated')
        self.do_request('reactivate_image', expected_status=204,
                        image_id=image['id'])
        resp = self.client.show_image(image_id=image['id'])
        self.assertTrue(resp['status'] == 'active')

        # Create a shared image within the persona user's project and make sure
        # we can reactivate it.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])
        resp = self.client.show_image(image_id=image['id'])
        self.assertTrue(resp['status'] == 'deactivated')
        self.do_request('reactivate_image', expected_status=204,
                        image_id=image['id'])
        resp = self.client.show_image(image_id=image['id'])
        self.assertTrue(resp['status'] == 'active')

        # Create a new user with authorization on a separate project.
        project_client = self.setup_user_client()

        # Create a private image in the separate project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])
        # The user can't reactivate this image because they can't find it.
        self.do_request('reactivate_image',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])
        # The user can't reactivate this image because they can't find it.
        self.do_request('reactivate_image',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'])

        # Only administrators can reactivate community images.
        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.admin_images_client.deactivate_image(image['id'])
        self.do_request('reactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

        # Only administrators can reactivate public images.
        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.admin_images_client.deactivate_image(image['id'])
        self.do_request('reactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'],
                        client=self.alt_project_images_client)


class NamespacesProjectMemberTests(rbac_base.MetadefV2RbacNamespaceTest,
                                   rbac_base.MetadefV2RbacNamespaceTemplate):

    credentials = ['project_member', 'project_alt_member',
                   'project_admin', 'project_alt_admin', 'primary']

    def test_get_namespace(self):

        def assertGetNamespace(actual_ns, owner, client):
            expected_status = 200
            if (actual_ns['visibility'] == 'private' and
                    actual_ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('show_namespace',
                            expected_status=expected_status,
                            client=client,
                            namespace=actual_ns['namespace'])

        actual_namespaces = self.create_namespaces()

        # Get namespace - member role from 'project' can access all
        # namespaces of it's own & only public namespace of 'alt_project'
        for actual_ns in actual_namespaces:
            assertGetNamespace(actual_ns, self.project_id,
                               self.namespace_client)

        # Get namespace - member role from 'alt_project' can access all
        # namespaces of it's own & only public namespace of 'project'
        for actual_ns in actual_namespaces:
            assertGetNamespace(actual_ns, self.alt_project_id,
                               self.alt_namespace_client)

    def test_list_namespaces(self):
        actual_namespaces = self.create_namespaces()

        # List namespace - member role from 'project' can access all
        # namespaces of it's own & only public namespace of 'alt_project'
        resp = self.do_request('list_namespaces',
                               client=self.namespace_client,
                               expected_status=200)
        self.assertListNamespaces(actual_namespaces, resp, self.project_id)

        # List namespace - member role from 'alt_project' can access all
        # namespaces of it's own & only public namespace of 'project'
        resp = self.do_request('list_namespaces',
                               client=self.alt_namespace_client,
                               expected_status=200)
        self.assertListNamespaces(actual_namespaces, resp, self.alt_project_id)

    def test_update_namespace(self):
        actual_namespaces = self.create_namespaces()

        def assertUpdateNamespace(actual_ns, owner, client):
            expected_status = exceptions.Forbidden
            if not (actual_ns['visibility'] == 'public' or
                    actual_ns['owner'] == owner):
                expected_status = exceptions.NotFound

            self.do_request('update_namespace',
                            expected_status=expected_status,
                            client=client,
                            description=data_utils.arbitrary_string(),
                            namespace=actual_ns['namespace'])

        # Check member role of 'project' is forbidden to update namespace
        for actual_ns in actual_namespaces:
            assertUpdateNamespace(actual_ns, self.project_id,
                                  self.namespace_client)

        # Check member role of 'alt_project' is forbidden to update namespace
        for actual_ns in actual_namespaces:
            assertUpdateNamespace(actual_ns, self.alt_project_id,
                                  self.alt_namespace_client)

    def test_create_namespace(self):
        # Check non-admin role of 'project' not allowed to create namespace
        self.do_request('create_namespace',
                        expected_status=exceptions.Forbidden,
                        client=self.namespace_client,
                        namespace=data_utils.arbitrary_string())

        # Check non-admin role of 'alt_project' not allowed to create namespace
        self.do_request('create_namespace',
                        expected_status=exceptions.Forbidden,
                        client=self.alt_namespace_client,
                        namespace=data_utils.arbitrary_string())

    def test_delete_namespace(self):
        actual_namespaces = self.create_namespaces()

        def assertDeleteNamespace(actual_ns, owner, client):
            expected_status = exceptions.Forbidden
            if not (actual_ns['visibility'] == 'public' or
                    actual_ns['owner'] == owner):
                expected_status = exceptions.NotFound

            self.do_request('delete_namespace',
                            expected_status=expected_status,
                            client=client,
                            namespace=actual_ns['namespace'])

        # Check member role of 'project' is forbidden to delete namespace
        for actual_ns in actual_namespaces:
            assertDeleteNamespace(actual_ns, self.project_id,
                                  self.namespace_client)

        # Check member role of 'alt_project' is forbidden to delete namespace
        for actual_ns in actual_namespaces:
            assertDeleteNamespace(actual_ns, self.alt_project_id,
                                  self.alt_namespace_client)

        # Verify the namespaces are not deleted
        for actual_ns in actual_namespaces:
            self.do_request('show_namespace',
                            expected_status=200,
                            client=self.admin_namespace_client,
                            namespace=actual_ns['namespace'])


class RSTypesProjectMemberTests(rbac_base.MetadefV2RbacResourceTypeTest,
                                rbac_base.MetadefV2RbacResourceTypeTemplate):

    credentials = ['project_member', 'project_alt_member', 'project_admin',
                   'project_alt_admin', 'primary']

    def test_create_resource_type(self):
        namespaces = self.create_namespaces()

        def assertRSTypeCreate(namespace, owner, client):
            rs_type_name = "rs_type_of_%s" % (namespace['namespace'])
            expected_status = exceptions.Forbidden
            if (namespace['visibility'] != 'public' and
                    namespace['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('create_resource_type_association',
                            expected_status=expected_status,
                            namespace_id=namespace['namespace'],
                            name=rs_type_name,
                            client=client)

        # Make sure non admin role of 'project' forbidden to
        # create resource types
        for namespace in namespaces:
            assertRSTypeCreate(namespace, self.project_id,
                               self.resource_types_client)

    def test_get_resource_type(self):
        ns_rs_types = self.create_resource_types()

        def assertRSTypeGet(actual_rs_type, client, owner):
            ns = actual_rs_type['namespace']
            expected_status = 200
            if (ns['visibility'] != 'public' and ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('list_resource_type_association',
                            expected_status=expected_status,
                            namespace_id=ns['namespace'],
                            client=client)

        # Get resource type - member role from 'project' can access all
        # resource types of it's own & only resource types having public
        # namespace of 'alt_project'
        for rs_type in ns_rs_types:
            assertRSTypeGet(rs_type, self.resource_types_client,
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

        def assertRSTypeDelete(actual_rs_type, client, owner):
            ns = actual_rs_type['namespace']
            expected_status = exceptions.Forbidden
            if (ns['visibility'] != 'public' and ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request(
                'delete_resource_type_association',
                expected_status=expected_status,
                namespace_id=ns['namespace'],
                resource_name=actual_rs_type['resource_type']['name'],
                client=client)

        # Make sure non admin role of 'project' not allowed to
        # delete resource types
        for rs_type in ns_rs_types:
            assertRSTypeDelete(rs_type, self.resource_types_client,
                               self.project_id)


class ObjectsProjectMemberTests(rbac_base.MetadefV2RbacObjectsTest,
                                rbac_base.MetadefV2RbacObjectsTemplate):

    credentials = ['project_member', 'project_alt_member', 'project_admin',
                   'project_alt_admin', 'primary']

    def test_create_object(self):
        namespaces = self.create_namespaces()

        def assertCreateObjects(namespace, owner, client):
            object_name = "object_of_%s" % (namespace['namespace'])
            expected_status = exceptions.Forbidden
            if (namespace['visibility'] == 'private' and
                    namespace['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('create_namespace_object',
                            expected_status=expected_status,
                            namespace=namespace['namespace'],
                            name=object_name,
                            client=client)

        # Make sure non admin role of 'project' forbidden to
        # create objects
        for namespace in namespaces:
            assertCreateObjects(namespace, self.project_id,
                                self.objects_client)

    def test_get_object(self):

        def assertObjectGet(actual_obj, owner, client):
            ns = actual_obj['namespace']
            expected_status = 200
            if (ns['visibility'] == 'private' and
                    ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('show_namespace_object',
                            expected_status=expected_status,
                            namespace=actual_obj['namespace']['namespace'],
                            object_name=actual_obj['object']['name'],
                            client=client)

        ns_objects = self.create_objects()

        # Get object - member role from 'project' can access all
        # objects of it's own & only objects having public namespace of
        # 'alt_project'
        for obj in ns_objects:
            assertObjectGet(obj, self.project_id, self.objects_client)

    def test_list_objects(self):
        ns_objects = self.create_objects()

        # list objects - member role from 'project' can access all
        # objects of it's own & only objects having public namespace of
        # 'alt_project'
        for obj in ns_objects:
            self.assertObjectsList(obj, self.objects_client, self.project_id)

    def test_update_object(self):

        def assertObjectUpdate(actual_object, owner, client):
            ns = actual_object['namespace']
            expected_status = exceptions.Forbidden
            if (ns['visibility'] == 'private' and
                    ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('update_namespace_object',
                            expected_status=expected_status,
                            name=actual_object['object']['name'],
                            description=data_utils.arbitrary_string(),
                            namespace=actual_object['namespace']['namespace'],
                            object_name=actual_object['object']['name'],
                            client=client)

        ns_objects = self.create_objects()
        # Make sure non admin role of 'project' not allowed to
        # update objects
        for obj in ns_objects:
            assertObjectUpdate(obj, self.project_id, self.objects_client)

    def test_delete_object(self):

        def assertObjectDelete(actual_obj, owner, client):
            ns = actual_obj['namespace']
            expected_status = exceptions.Forbidden
            if (ns['visibility'] == 'private' and
                    ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('delete_namespace_object',
                            expected_status=expected_status,
                            namespace=actual_obj['namespace']['namespace'],
                            object_name=actual_obj['object']['name'],
                            client=client)

        ns_objects = self.create_objects()
        # Make sure non admin role of 'project' not allowed to
        # delete objects
        for obj in ns_objects:
            assertObjectDelete(obj, self.project_id, self.objects_client)


class PropertiesProjectMemberTests(rbac_base.MetadefV2RbacPropertiesTest,
                                   rbac_base.MetadefV2RbacPropertiesTemplate):

    credentials = ['project_member', 'project_alt_member',
                   'project_admin', 'project_alt_admin', 'primary']

    def test_create_property(self):
        namespaces = self.create_namespaces()

        def assertPropertyCreate(namespace, client, owner=None):
            property_name = "prop_of_%s" % (namespace['namespace'])
            expected_status = exceptions.Forbidden
            if not (namespace['visibility'] == 'public' or
                    namespace['owner'] == owner):
                expected_status = exceptions.NotFound

            self.do_request('create_namespace_property',
                            expected_status=expected_status,
                            namespace=namespace['namespace'],
                            title="property",
                            type='integer',
                            name=property_name,
                            client=client)
        # Make sure non admin role of 'project' forbidden to
        # create properties
        for namespace in namespaces:
            assertPropertyCreate(namespace, self.properties_client,
                                 self.project_id)

    def test_get_properties(self):
        ns_properties = self.create_properties()

        def assertPropertyGet(actual_prop, client, owner=None):
            ns = actual_prop['namespace']
            expected_status = 200
            if (ns['visibility'] != 'public' and
                    ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('show_namespace_properties',
                            expected_status=expected_status,
                            namespace=ns['namespace'],
                            property_name=actual_prop['property']['name'],
                            client=client)

        # Get property - member role from 'project' can access all
        # properties of it's own & only propertys having public namespace of
        # 'alt_project'
        for prop in ns_properties:
            assertPropertyGet(prop, self.properties_client, self.project_id)

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

        def assertPropertyUpdate(actual_prop, client, owner=None):
            ns = actual_prop['namespace']
            expected_status = exceptions.Forbidden
            if (ns['visibility'] != 'public' and
                    ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('update_namespace_properties',
                            expected_status=expected_status,
                            name=actual_prop['property']['name'],
                            description=data_utils.arbitrary_string(),
                            namespace=ns['namespace'],
                            property_name=actual_prop['property']['name'],
                            title="UPDATE_Property",
                            type="string",
                            client=client)

        # Make sure non admin role of 'project' not allowed to
        # update properties
        for prop in ns_properties:
            assertPropertyUpdate(prop, self.properties_client,
                                 self.project_id)

    def test_delete_properties(self):
        ns_properties = self.create_properties()

        def assertPropertyDelete(actual_prop, client, owner=None):
            ns = actual_prop['namespace']
            expected_status = exceptions.Forbidden
            if (ns['visibility'] != 'public' and
                    ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('delete_namespace_property',
                            expected_status=expected_status,
                            namespace=ns['namespace'],
                            property_name=actual_prop['property']['name'],
                            client=client)

        # Make sure non admin role of 'project' not allowed to
        # delete properties
        for prop in ns_properties:
            assertPropertyDelete(prop, self.properties_client,
                                 self.project_id)


class TagsProjectMemberTests(rbac_base.MetadefV2RbacTagsTest,
                             rbac_base.MetadefV2RbacTagsTemplate):

    credentials = ['project_member', 'project_alt_member',
                   'project_admin', 'project_alt_admin', 'primary']

    def test_create_tag(self):
        namespaces = self.create_namespaces()

        def assertTagsCreate(namespace, client, owner, multiple_tags=False):
            expected_status = exceptions.Forbidden
            if (namespace['visibility'] != 'public' and
                    namespace['owner'] != owner):
                expected_status = exceptions.NotFound

            if multiple_tags:
                multiple_tags = [{"name": "tag1"}, {"name": "tag2"},
                                 {"name": "tag3"}]
                self.do_request('create_namespace_tags',
                                expected_status=expected_status,
                                namespace=namespace['namespace'],
                                tags=multiple_tags,
                                client=client)
            else:
                tag_name = "tag_of_%s" % (namespace['namespace'])
                self.do_request('create_namespace_tag',
                                expected_status=expected_status,
                                namespace=namespace['namespace'],
                                tag_name=tag_name,
                                client=client)

        # Make sure non admin role of 'project' forbidden to
        # create tags
        for namespace in namespaces:
            assertTagsCreate(namespace, self.tags_client, self.project_id)

            # Create Multiple Tags
            assertTagsCreate(namespace, self.tags_client, self.project_id,
                             multiple_tags=True)

    def test_get_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)

        def assertTagGet(actual_tag, client, owner=None):
            ns = actual_tag['namespace']
            expected_status = 200
            if (ns['visibility'] != 'public' and ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('show_namespace_tag',
                            expected_status=expected_status,
                            namespace=ns['namespace'],
                            tag_name=actual_tag['tag']['name'],
                            client=client)

        # Get tag - member role from 'project' can access all
        # tags of it's own & only tags having public namespace of
        # 'alt_project'
        for tag in ns_tags:
            assertTagGet(tag, self.tags_client, self.project_id)

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

        def assertTagUpdate(tag, client, owner):
            ns = tag['namespace']
            expected_status = exceptions.Forbidden
            if (ns['visibility'] != 'public' and ns['owner'] != owner):
                expected_status = exceptions.NotFound

            self.do_request('update_namespace_tag',
                            expected_status=expected_status,
                            name=data_utils.arbitrary_string(),
                            namespace=tag['namespace']['namespace'],
                            tag_name=tag['tag']['name'],
                            client=client)

        # Make sure non admin role of 'project' not allowed to
        # update tags
        for tag in ns_tags:
            assertTagUpdate(tag, self.tags_client, self.project_id)

    def test_delete_tags(self):
        namespaces = self.create_namespaces()
        ns_tags = self.create_tags(namespaces)

        def assertTagsDelete(actual_tag, client, owner, multiple_tags=False):
            ns = tag['namespace']
            expected_status = exceptions.Forbidden
            if (ns['visibility'] != 'public' and ns['owner'] != owner):
                expected_status = exceptions.NotFound

            if multiple_tags:
                self.do_request('delete_namespace_tags',
                                expected_status=expected_status,
                                namespace=ns['namespace'],
                                client=client)
            else:
                self.do_request('delete_namespace_tag',
                                expected_status=expected_status,
                                namespace=ns['namespace'],
                                tag_name=actual_tag['tag']['name'],
                                client=client)

        # Make sure non admin role of 'project' not allowed to
        # delete tags
        for tag in ns_tags:
            assertTagsDelete(tag, self.tags_client, self.project_id)

        # Create Multiple Tags
        ns_multiple_tags = self.create_tags(namespaces, multiple_tags=True)
        # Make sure non admin role of 'project' not allowed to
        # delete multiple tags
        for tags in ns_multiple_tags:
            assertTagsDelete(tags, self.tags_client, self.project_id,
                             multiple_tags=True)
