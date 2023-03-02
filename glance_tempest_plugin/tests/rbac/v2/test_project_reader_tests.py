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

from glance_tempest_plugin.tests.rbac.v2 import test_project_members_tests

CONF = config.CONF


class ImagesProjectReaderTests(
        test_project_members_tests.ImagesProjectMemberTests):

    credentials = ['project_reader', 'project_admin', 'system_admin',
                   'admin', 'project_alt_admin', 'project_alt_member',
                   'project_alt_reader']

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.alt_project_images_client = (
            cls.os_project_alt_reader.image_client_v2)

    @decorators.idempotent_id('5e151433-5901-45ec-9451-ed3170c299cb')
    def test_create_image(self):
        # Project readers can't create images.
        self.do_request('create_image', expected_status=exceptions.Forbidden,
                        **self.image(visibility='private'))

        self.do_request('create_image', expected_status=exceptions.Forbidden,
                        **self.image(visibility='shared'))

        self.do_request('create_image', expected_status=exceptions.Forbidden,
                        **self.image(visibility='community'))

        self.do_request('create_image', expected_status=exceptions.Forbidden,
                        **self.image(visibility='public'))

    @decorators.idempotent_id('6de1e04c-d0cd-45b3-8007-3712bbca817d')
    def test_list_images(self):
        super().test_list_images()

    @decorators.idempotent_id('f402e6a2-7cc9-46c0-b6c2-a235f5512788')
    def test_get_image(self):
        super().test_get_image()

    @decorators.idempotent_id('f2be46ee-317b-4825-9d3d-bd23a1fb7858')
    def test_update_image(self):
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'], patch=patch_body)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'], patch=patch_body)

        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        # This fails because getting an image outside the user's project
        # returns a 404.
        self.do_request('update_image', expected_status=exceptions.NotFound,
                        image_id=image['id'], patch=patch_body,
                        client=self.alt_project_images_client)

        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        # FIXME(lbragstad): This is different from the status code for
        # project-admininstrators because the database layer allows users with
        # the admin role the ability to view images outside their project, and
        # returns a 403 because it checks tenancy later. IMO, this return code
        # shouldn't be any different from project users.
        self.do_request('update_image', expected_status=exceptions.NotFound,
                        image_id=image['id'], patch=patch_body,
                        client=self.alt_project_images_client)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        # Same comment as above with updating private images for other
        # projects.
        self.do_request('update_image', expected_status=exceptions.NotFound,
                        image_id=image['id'], patch=patch_body)

        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'], patch=patch_body)

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        name = data_utils.rand_name('new-image-name')
        patch_body = [dict(replace='/name', value=name)]
        self.do_request('update_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'], patch=patch_body)

    @decorators.idempotent_id('b7ac2883-f569-4032-a35b-a79ef1277582')
    def test_upload_image(self):
        file_contents = data_utils.random_bytes()
        image_data = six.BytesIO(file_contents)

        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'], data=image_data)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file',
                        expected_status=exceptions.Forbidden,
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

        # This fails because the user can't actually see the image since it's
        # not shared with them.
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
                        image_id=image['id'], data=image_data)

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('store_image_file',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'], data=image_data)

    @decorators.idempotent_id('9067339d-c64b-4e4d-bc0e-a52cd1365ea3')
    def test_download_image(self):
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('show_image_file',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('show_image_file',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        project_client = self.setup_user_client()

        # Fail to download an image for another project because we can't find
        # it.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('show_image_file',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'])

        # Fail to download an image for another project because we can't find
        # it.
        image = self.admin_images_client.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image,
                        image['id'])
        self.do_request('show_image_file',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'],
                        client=self.alt_project_images_client)

        # Fail to download an image for another project because we can't find
        # it.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image_file',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image_file',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('show_image_file',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

    @decorators.idempotent_id('e8c3382c-c547-49c1-a92e-fa1d6378d4df')
    def test_delete_image(self):
        # Project readers can't delete images outside their project. This is
        # returned as an HTTP 404 instead of an HTTP 403 because they can't
        # find the image they're trying to delete.
        project_client = self.setup_user_client()
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('delete_image', expected_status=exceptions.NotFound,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('delete_image', expected_status=exceptions.NotFound,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('delete_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        # Project readers can't delete images inside their project, regardless
        # of the image state (private, shared, community, or public).
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('delete_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('delete_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        image = project_client.image_client_v2.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('delete_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        # Project readers can't delete public images.
        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('delete_image', expected_status=exceptions.Forbidden,
                        image_id=image['id'])

    @decorators.idempotent_id('8eaddc1a-f9d0-4a68-8fef-1951c328d01c')
    def test_add_image_member(self):
        # Create a new user with authorization on a separate project.
        member_client = self.setup_user_client()
        member_project_id = member_client.credentials.project_id

        # Create a new user with authorization on the persona user's project.
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)

        # Create a shared image and make sure we can't share the image with
        # other projects.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.do_request('create_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'],
                        member=member_project_id)

    @decorators.idempotent_id('e0feceab-dfc0-4d08-88be-81f5d225c72f')
    def test_update_image_member(self):
        # Create a new user with authorization on a separate project.
        project_client = self.setup_user_client()

        # Create a shared image in the other project and add the persona user's
        # project as a member.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=self.persona.credentials.project_id)

        # Make sure the user can't accept the image.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'],
                        member_id=self.persona.credentials.project_id,
                        status='accepted')

        # Make sure the user can't reject the change.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'],
                        member_id=self.persona.credentials.project_id,
                        status='rejected')

        # Create a new user with authorization on a separate project.
        member_client = self.setup_user_client()
        member_project_id = member_client.credentials.project_id

        # Have the original project client create a new shared image and share
        # it with the new member project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)

        # Make sure the user can't accept images for project they have no
        # authorization to know about.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], member_id=member_project_id,
                        status='accepted')

        # Make sure the user can't reject images for project they have no
        # authorization to know about.
        self.do_request('update_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], member_id=member_project_id,
                        status='rejected')

    @decorators.idempotent_id('864e275e-2238-4b0f-9039-9bc7aed22f92')
    def test_delete_image_member(self):
        # Create a new user with authorization on a separate project.
        member_client = self.setup_user_client()
        member_project_id = member_client.credentials.project_id

        # Create a new user with authorization on the persona user's project.
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)

        # Create a shared image in the persona user's project and share it with
        # the member project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)

        # Make sure the user can't delete image members.
        self.do_request('delete_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'], member_id=member_project_id)

        # Create a new user with authorization on a separate project.
        project_client = self.setup_user_client()

        # Creata a shared image in that new project and share it with the
        # member project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_member_client_v2.create_image_member(
            image['id'], member=member_project_id)

        # Make sure the user can't delete image members from images they have
        # no authorization to know about.
        self.do_request('delete_image_member',
                        client=self.persona.image_member_client_v2,
                        expected_status=exceptions.NotFound,
                        image_id=image['id'], member_id=member_project_id)

    @decorators.idempotent_id('310672b0-bf63-4ce0-b3c4-5230b8e7de31')
    def test_deactivate_image(self):
        # Create a new user with authorization on the persona user's project.
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        file_contents = data_utils.random_bytes()
        image_data = six.BytesIO(file_contents)

        # Create a new private image in the persona user's project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)

        # Make sure they can't deactivate images, even in their own project.
        self.do_request('deactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        # Create a new shared image in the persona user's project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)

        # Make sure they can't deactivate images, even in their own project.
        self.do_request('deactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        # Create a new user with authorization on a separate project.
        project_client = self.setup_user_client()

        # Create a private image in the new project.
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
                        image_id=image['id'])

        # Only administrators can deactivate community images.
        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.do_request('deactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        # Only administrators can deactivate public images.
        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.do_request('deactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

    @decorators.idempotent_id('0d1fc51c-d4c9-4dd5-9f21-c28b09d3f9ec')
    def test_reactivate_image(self):
        # Create a new user with authorization on the persona user's project.
        project_id = self.persona.credentials.project_id
        project_client = self.setup_user_client(project_id=project_id)
        file_contents = data_utils.random_bytes()
        image_data = six.BytesIO(file_contents)

        # Create a private image in the persona user's project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])

        # Make sure the user can't reactivate private images, even in their own
        # project.
        self.do_request('reactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        # Create a shared image in the persona user's project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='shared'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])

        # Make sure the user can't reactivate shared images, even in their own
        # project.
        self.do_request('reactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        # Create a new user with authorization on a separate project.
        project_client = self.setup_user_client()

        # Create a private image in the new project.
        image = project_client.image_client_v2.create_image(
            **self.image(visibility='private'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        project_client.image_client_v2.store_image_file(image['id'],
                                                        image_data)
        project_client.image_client_v2.deactivate_image(image['id'])

        # The user can't reactivate this image because they can't find it.
        self.do_request('reactivate_image',
                        expected_status=exceptions.NotFound,
                        image_id=image['id'])

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

        # Create a community image.
        image = self.admin_images_client.create_image(
            **self.image(visibility='community'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.admin_images_client.deactivate_image(image['id'])

        # Make sure the user can't reactivate community images.
        self.do_request('reactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])

        # Create a public image.
        image = self.admin_images_client.create_image(
            **self.image(visibility='public'))
        self.addCleanup(self.admin_images_client.delete_image, image['id'])
        self.admin_images_client.store_image_file(image['id'], image_data)
        self.admin_images_client.deactivate_image(image['id'])

        # Make sure the user can't reactivate public images.
        self.do_request('reactivate_image',
                        expected_status=exceptions.Forbidden,
                        image_id=image['id'])


class NamespacesProjectReaderTests(
        test_project_members_tests.NamespacesProjectMemberTests):
    credentials = ['project_reader', 'project_alt_reader',
                   'project_admin', 'project_alt_admin', 'primary']


class RSTypesProjectReaderTests(
        test_project_members_tests.RSTypesProjectMemberTests):

    credentials = ['project_reader', 'project_alt_reader', 'project_admin',
                   'project_alt_admin', 'primary']


class ObjectsProjectReaderTests(
        test_project_members_tests.ObjectsProjectMemberTests):

    credentials = ['project_reader', 'project_alt_reader', 'project_admin',
                   'project_alt_admin', 'primary']


class PropertiesProjectReaderTests(
        test_project_members_tests.PropertiesProjectMemberTests):

    credentials = ['project_reader', 'project_alt_reader',
                   'project_admin', 'project_alt_admin', 'primary']


class TagsProjectReaderTests(
        test_project_members_tests.TagsProjectMemberTests):

    credentials = ['project_reader', 'project_alt_reader',
                   'project_admin', 'project_alt_admin', 'primary']
