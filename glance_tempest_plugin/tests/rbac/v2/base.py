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

import abc

from tempest.api.image import base
from tempest import clients
from tempest import config
from tempest.lib import auth
from tempest.lib.common.utils import data_utils
from tempest.lib.common.utils import test_utils
from tempest.lib import exceptions

CONF = config.CONF


class RbacBaseTests(base.BaseV2ImageTest):

    identity_version = 'v3'

    @classmethod
    def skip_checks(cls):
        super().skip_checks()
        if not CONF.enforce_scope.glance:
            raise cls.skipException("enforce_scope is not enabled for "
                                    "glance, skipping RBAC tests")

    def do_request(self, method, expected_status=200, client=None, **payload):
        if not client:
            client = self.client
        if isinstance(expected_status, type(Exception)):
            self.assertRaises(expected_status,
                              getattr(client, method),
                              **payload)
        else:
            response = getattr(client, method)(**payload)
            self.assertEqual(response.response.status, expected_status)
            return response

    def setup_user_client(self, project_id=None):
        """Set up project user with its own client.

        This is useful for testing protection of resources in separate
        projects.

        Returns a client object and the user's ID.
        """
        user_dict = {
            'name': data_utils.rand_name('user'),
            'password': data_utils.rand_password(),
        }
        user_id = self.os_system_admin.users_v3_client.create_user(
            **user_dict)['user']['id']
        self.addCleanup(self.os_system_admin.users_v3_client.delete_user,
                        user_id)

        if not project_id:
            project_id = self.os_system_admin.projects_client.create_project(
                data_utils.rand_name())['project']['id']
            self.addCleanup(
                self.os_system_admin.projects_client.delete_project,
                project_id)

        member_role_id = self.os_system_admin.roles_v3_client.list_roles(
            name='member')['roles'][0]['id']
        self.os_system_admin.roles_v3_client.create_user_role_on_project(
            project_id, user_id, member_role_id)
        creds = auth.KeystoneV3Credentials(
            user_id=user_id,
            password=user_dict['password'],
            project_id=project_id)
        auth_provider = clients.get_auth_provider(creds)
        creds = auth_provider.fill_credentials()
        client = clients.Manager(credentials=creds)
        return client


def namespace(name, owner, visibility='private', protected=False):
    return {'namespace': name, 'visibility': visibility,
            'description': data_utils.arbitrary_string(),
            'display_name': name, 'owner': owner, 'protected': protected}


class RbacMetadefBase(RbacBaseTests):
    def create_namespaces(self):
        """Create private and public namespaces for different projects."""
        project_namespaces = []
        alt_namespaces = []
        for visibility in ['public', 'private']:
            project_ns = "%s_%s_%s" % (
                self.project_id,
                visibility,
                self.__class__.__name__)

            alt_ns = "%s_%s_%s" % (self.alt_project_id, visibility,
                                   self.__class__.__name__)

            project_namespace = \
                self.os_project_admin.namespaces_client.create_namespace(
                    **namespace(project_ns, self.project_id,
                                visibility=visibility))
            project_namespaces.append(project_namespace)
            self.addCleanup(
                test_utils.call_and_ignore_notfound_exc,
                self.os_project_admin.namespaces_client.delete_namespace,
                project_ns)

            alt_namespace = \
                self.os_project_admin.namespaces_client.create_namespace(
                    **namespace(alt_ns, self.alt_project_id,
                                visibility=visibility))
            alt_namespaces.append(alt_namespace)
            self.addCleanup(
                test_utils.call_and_ignore_notfound_exc,
                self.os_project_admin.namespaces_client.delete_namespace,
                alt_ns)

        return project_namespaces + alt_namespaces


class ImageV2RbacImageTest(RbacBaseTests):

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.persona = getattr(cls, f'os_{cls.credentials[0]}')
        cls.client = cls.persona.image_client_v2
        # FIXME(lbragstad): This should use os_system_admin when glance
        # supports system scope.
        cls.admin_client = cls.os_project_admin
        cls.admin_images_client = cls.admin_client.image_client_v2

    @classmethod
    def setup_credentials(cls):
        super().setup_credentials()
        cls.os_primary = getattr(cls, f'os_{cls.credentials[0]}')

    def image(self, visibility=None):
        image = {}
        image['name'] = data_utils.rand_name('image')
        # NOTE(danms): It's technically possible that bare/raw is not allowed,
        # but this test suite cannot operate in that scenario since it does
        # not have valid image data to upload.
        if 'bare' not in CONF.image.container_formats:
            self.skipTest('This test requires the "bare" container format')
        if 'raw' not in CONF.image.disk_formats:
            self.skipTest('This test requires the "raw" container format')
        image['container_format'] = 'bare'
        image['disk_format'] = 'raw'
        image['visibility'] = visibility if visibility else 'private'
        image['ramdisk_uuid'] = '00000000-1111-2222-3333-444455556666'
        return image


class ImageV2RbacTemplate(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def test_create_image(self):
        """Test add_image policy.

        This test must check:
          * whether the persona can create a private image
          * whether the persona can create a shared image
          * whether the persona can create a community image
          * whether the persona can create a public image
        """

    @abc.abstractmethod
    def test_get_image(self):
        """Test get_image policy.

        This test must check:
          * whether a persona can get a private image
          * whether a persona can get a shared image
          * whether a persona can get a community image
          * whether a persona can get a public image
        """

    @abc.abstractmethod
    def test_list_images(self):
        """Test get_images policy.

        This test must check:
          * whether the persona can list private images within their project
          * whether the persona can list shared images
          * whether the persona can list community images
          * whether the persona can list public images
        """

    @abc.abstractmethod
    def test_update_image(self):
        """Test modify_image policy.

        This test must check:
          * whether the persona can modify private images
          * whether the persona can modify shared images
          * whether the persona can modify community images
          * whether the persona can modify public images
        """

    @abc.abstractmethod
    def test_upload_image(self):
        """Test upload_image policy.

        This test must check:
          * whether the persona can upload private images
          * whether the persona can upload shared images
          * whether the persona can upload community images
          * whether the persona can upload public images
        """

    @abc.abstractmethod
    def test_download_image(self):
        """Test download_image policy.

        This test must check:
          * whether the persona can download private images
          * whether the persona can download shared images
          * whether the persona can download community images
          * whether the persona can download public images
        """

    @abc.abstractmethod
    def test_delete_image(self):
        """Test delete_image policy.

        This test must check:
          * whether the persona can delete a private image
          * whether the persona can delete a shared image
          * whether the persona can delete a community image
          * whether the persona can delete a public image
          * whether the persona can delete an image outside their project
        """

    @abc.abstractmethod
    def test_add_image_member(self):
        pass

    @abc.abstractmethod
    def test_get_image_member(self):
        pass

    @abc.abstractmethod
    def test_list_image_members(self):
        pass

    @abc.abstractmethod
    def test_update_image_member(self):
        pass

    @abc.abstractmethod
    def test_delete_image_member(self):
        pass

    @abc.abstractmethod
    def test_deactivate_image(self):
        pass

    @abc.abstractmethod
    def test_reactivate_image(self):
        pass


class MetadefV2RbacNamespaceTest(RbacMetadefBase):
    @classmethod
    def setup_clients(cls):
        super(MetadefV2RbacNamespaceTest, cls).setup_clients()
        if 'project_member' in cls.credentials:
            persona = 'project_member'
            alt_persona = 'project_alt_member'
        elif 'project_reader' in cls.credentials:
            persona = 'project_reader'
            alt_persona = 'project_alt_reader'
        else:
            persona = 'project_admin'
            alt_persona = 'project_alt_admin'
        cls.persona = getattr(cls, 'os_%s' % persona)
        cls.alt_persona = getattr(cls, 'os_%s' % alt_persona)
        cls.project_id = cls.persona.namespaces_client.project_id
        cls.alt_project_id = cls.alt_persona.namespaces_client.project_id
        cls.admin_namespace_client = cls.os_project_admin.namespaces_client
        cls.namespaces_client = cls.persona.namespaces_client
        cls.namespace_client = cls.persona.namespaces_client
        cls.alt_namespace_client = cls.alt_persona.namespaces_client

    def assertListNamespaces(self, actual, expected, owner=None):
        expected_ns = set(ns['namespace'] for ns in expected['namespaces'])
        if owner:
            for ns in actual:
                if (ns['visibility'] == 'private' and
                        ns['owner'] != owner):
                    self.assertNotIn(ns['namespace'], expected_ns)
                else:
                    self.assertIn(ns['namespace'], expected_ns)
        else:
            for ns in actual:
                self.assertIn(ns['namespace'], expected_ns)

    def assertGetNamespace(self, actual_ns, owner, client):
        expected_status = 200
        if (actual_ns['visibility'] == 'private' and
                actual_ns['owner'] != owner):
            expected_status = exceptions.NotFound

        self.do_request('show_namespace',
                        expected_status=expected_status,
                        client=client,
                        namespace=actual_ns['namespace'])

    def assertUpdateNamespace(self, actual_ns, owner, client):
        expected_status = exceptions.Forbidden
        if not (actual_ns['visibility'] == 'public' or
                actual_ns['owner'] == owner):
            expected_status = exceptions.NotFound

        self.do_request('update_namespace',
                        expected_status=expected_status,
                        client=client,
                        description=data_utils.arbitrary_string(),
                        namespace=actual_ns['namespace'])

    def assertDeleteNamespace(self, actual_ns, owner, client):
        expected_status = exceptions.Forbidden
        if not (actual_ns['visibility'] == 'public' or
                actual_ns['owner'] == owner):
            expected_status = exceptions.NotFound

        self.do_request('delete_namespace',
                        expected_status=expected_status,
                        client=client,
                        namespace=actual_ns['namespace'])


class MetadefV2RbacNamespaceTemplate(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def test_get_namespace(self):
        """Test get_metadef_namespace policy."""
        pass

    @abc.abstractmethod
    def test_list_namespaces(self):
        """Test get_metadef_namespaces policy."""
        pass

    @abc.abstractmethod
    def test_update_namespace(self):
        """Test modify_metadef_namespace policy."""
        pass

    @abc.abstractmethod
    def test_create_namespace(self):
        """Test add_metadef_namespace policy."""
        pass

    @abc.abstractmethod
    def test_delete_namespace(self):
        """Test delete_metadef_namespace policy."""
        pass


class MetadefV2RbacResourceTypeTest(RbacMetadefBase):
    @classmethod
    def setup_clients(cls):
        super(MetadefV2RbacResourceTypeTest, cls).setup_clients()
        if 'project_member' in cls.credentials:
            persona = 'project_member'
            alt_persona = 'project_alt_member'
        elif 'project_reader' in cls.credentials:
            persona = 'project_reader'
            alt_persona = 'project_alt_reader'
        else:
            persona = 'project_admin'
            alt_persona = 'project_alt_admin'
        cls.persona = getattr(cls, 'os_%s' % persona)
        cls.alt_persona = getattr(cls, 'os_%s' % alt_persona)
        cls.project_id = cls.persona.namespaces_client.project_id
        cls.alt_project_id = cls.alt_persona.namespaces_client.project_id
        cls.resource_types_client = cls.persona.resource_types_client

    def create_resource_types(self, namespace=None, owner=None, client=None,
                              is_admin=True):
        namespace_resource_types = []
        if is_admin:
            # Create namespace for two different projects
            namespaces = self.create_namespaces()

            for ns in namespaces:
                alt_client = None
                if ns['namespace'].startswith(self.alt_project_id):
                    alt_client = \
                        self.os_project_alt_admin.resource_types_client
                    client = alt_client
                if alt_client is None:
                    client = self.os_project_admin.resource_types_client

                resource_name = "rs_type_of_%s" % (ns['namespace'])
                resource_type = client.create_resource_type_association(
                    ns['namespace'], name=resource_name)
                resource_types = {'namespace': ns,
                                  'resource_type': resource_type}
                namespace_resource_types.append(resource_types)
        else:
            rs_type_name = "rs_type_of_%s" % (namespace['namespace'])
            expected_status = exceptions.Forbidden
            if not (namespace['visibility'] == 'public' or
                    namespace['owner'] == owner):
                expected_status = exceptions.NotFound

            self.do_request('create_resource_type_association',
                            expected_status=expected_status,
                            namespace_id=namespace['namespace'],
                            name=rs_type_name,
                            client=client)

        return namespace_resource_types

    def assertRSTypeList(self, ns_rs_types, resp):
        actual_rs_types = set(rt['name'] for rt in resp['resource_types'])

        for rs_type in ns_rs_types:
            self.assertIn(rs_type['resource_type']['name'],
                          actual_rs_types)

    def assertRSTypeGet(self, actual_rs_type, client, owner):
        ns = actual_rs_type['namespace']
        expected_status = 200
        if (ns['visibility'] != 'public' and ns['owner'] != owner):
            expected_status = exceptions.NotFound

        self.do_request('list_resource_type_association',
                        expected_status=expected_status,
                        namespace_id=ns['namespace'],
                        client=client)

    def assertRSTypeDelete(self, actual_rs_type, client, owner):
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


class MetadefV2RbacResourceTypeTemplate(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def test_create_resource_type(self):
        """Test add_metadef_resource_type_association policy."""
        pass

    @abc.abstractmethod
    def test_get_resource_type(self):
        """Test get_metadef_resource_type policy."""
        pass

    @abc.abstractmethod
    def test_list_resource_types(self):
        """Test list_metadef_resource_types policy."""
        pass

    @abc.abstractmethod
    def test_delete_resource_type(self):
        """Test remove_metadef_resource_type_association policy."""
        pass


class MetadefV2RbacObjectsTest(RbacMetadefBase):
    @classmethod
    def setup_clients(cls):
        super(MetadefV2RbacObjectsTest, cls).setup_clients()
        if 'project_member' in cls.credentials:
            persona = 'project_member'
            alt_persona = 'project_alt_member'
        elif 'project_reader' in cls.credentials:
            persona = 'project_reader'
            alt_persona = 'project_alt_reader'
        else:
            persona = 'project_admin'
            alt_persona = 'project_alt_admin'
        cls.persona = getattr(cls, 'os_%s' % persona)
        cls.alt_persona = getattr(cls, 'os_%s' % alt_persona)
        cls.project_id = cls.persona.namespace_objects_client.project_id
        cls.alt_project_id = \
            cls.alt_persona.namespace_objects_client.project_id
        cls.objects_client = cls.persona.namespace_objects_client

    def create_objects(self, namespace=None, owner=None, client=None,
                       is_admin=True):
        namespace_objects = []
        if is_admin:
            # Create namespace for two different projects
            namespaces = self.create_namespaces()
            for ns in namespaces:
                alt_client = None
                if ns['namespace'].startswith(self.alt_project_id):
                    alt_client = \
                        self.os_project_alt_admin.namespace_objects_client
                    client = alt_client
                if alt_client is None:
                    client = self.os_project_admin.namespace_objects_client
                object_name = "object_of_%s" % (ns['namespace'])
                namespace_object = client.create_namespace_object(
                    ns['namespace'], name=object_name,
                    description=data_utils.arbitrary_string())
                obj = {'namespace': ns, 'object': namespace_object}
                namespace_objects.append(obj)
        else:
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
        return namespace_objects

    def assertObjectsList(self, actual_obj, client, owner=None):
        ns = actual_obj['namespace']
        if owner:
            if not (ns['visibility'] == 'public' or
                    ns['owner'] == owner):
                self.do_request('list_namespace_objects',
                                expected_status=exceptions.NotFound,
                                namespace=ns['namespace'],
                                client=client)
            else:
                resp = self.do_request('list_namespace_objects',
                                       expected_status=200,
                                       namespace=ns['namespace'],
                                       client=client)
                self.assertIn(actual_obj['object']['name'],
                              resp['objects'][0]['name'])
        else:
            resp = self.do_request('list_namespace_objects',
                                   expected_status=200,
                                   namespace=ns['namespace'],
                                   client=client)
            self.assertIn(actual_obj['object']['name'],
                          resp['objects'][0]['name'])

    def assertObjectGet(self, actual_obj, owner, client):
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

    def assertObjectUpdate(self, actual_object, owner, client):
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

    def assertObjectDelete(self, actual_obj, owner, client):
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


class MetadefV2RbacObjectsTemplate(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def test_create_object(self):
        """Test add_metadef_object policy."""
        pass

    @abc.abstractmethod
    def test_get_object(self):
        """Test get_metadef_object policy."""
        pass

    @abc.abstractmethod
    def test_list_objects(self):
        """Test list_metadef_objects policy."""
        pass

    @abc.abstractmethod
    def test_update_object(self):
        """Test update_metadef_object policy."""
        pass

    @abc.abstractmethod
    def test_delete_object(self):
        """Test delete_metadef_object policy."""
        pass


class MetadefV2RbacPropertiesTest(RbacMetadefBase):
    @classmethod
    def setup_clients(cls):
        super(MetadefV2RbacPropertiesTest, cls).setup_clients()
        if 'project_member' in cls.credentials:
            persona = 'project_member'
            alt_persona = 'project_alt_member'
        elif 'project_reader' in cls.credentials:
            persona = 'project_reader'
            alt_persona = 'project_alt_reader'
        else:
            persona = 'project_admin'
            alt_persona = 'project_alt_admin'
        cls.persona = getattr(cls, 'os_%s' % persona)
        cls.alt_persona = getattr(cls, 'os_%s' % alt_persona)
        cls.project_id = cls.persona.namespaces_client.project_id
        cls.alt_project_id = cls.alt_persona.namespaces_client.project_id
        cls.properties_client = cls.persona.namespace_properties_client

    def create_properties(self, namespace=None, owner=None, client=None,
                          is_admin=True):
        namespace_properties = []
        if is_admin:
            # Create namespace for two different projects
            namespaces = self.create_namespaces()
            for ns in namespaces:
                alt_client = None
                if ns['namespace'].startswith(self.alt_project_id):
                    alt_client = \
                        self.os_project_alt_admin.namespace_properties_client
                    client = alt_client
                if alt_client is None:
                    client = self.os_project_admin.namespace_properties_client
                property_name = "prop_of_%s" % (ns['namespace'])
                namespace_property = client.create_namespace_property(
                    ns['namespace'], name=property_name, title='property',
                    type='integer')
                prop = {'namespace': ns, 'property': namespace_property}
                namespace_properties.append(prop)
        else:
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
        return namespace_properties

    def assertPropertyList(self, actual_prop, client, owner=None):
        ns = actual_prop['namespace']
        if owner:
            if not (ns['visibility'] == 'public' or ns['owner'] == owner):
                resp = self.do_request('list_namespace_properties',
                                       expected_status=exceptions.NotFound,
                                       client=client,
                                       namespace=ns['namespace'])
            else:
                resp = self.do_request('list_namespace_properties',
                                       expected_status=200,
                                       client=client,
                                       namespace=ns['namespace'])
                self.assertEqual(actual_prop['property']['name'],
                                 [*resp['properties']][0])
        else:
            resp = self.do_request('list_namespace_properties',
                                   expected_status=200,
                                   client=client,
                                   namespace=ns['namespace'])
            self.assertEqual(actual_prop['property']['name'],
                             [*resp['properties']][0])

    def assertPropertyGet(self, actual_prop, client, owner=None):
        ns = actual_prop['namespace']
        expected_status = 200
        if (ns['visibility'] != 'public' and ns['owner'] != owner):
            expected_status = exceptions.NotFound
        self.do_request('show_namespace_properties',
                        expected_status=expected_status,
                        namespace=ns['namespace'],
                        property_name=actual_prop['property']['name'],
                        client=client)

    def assertPropertyUpdate(self, actual_prop, client, owner=None):
        ns = actual_prop['namespace']
        expected_status = exceptions.Forbidden
        if (ns['visibility'] != 'public' and ns['owner'] != owner):
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

    def assertPropertyDelete(self, actual_prop, client, owner=None):
        ns = actual_prop['namespace']
        expected_status = exceptions.Forbidden
        if (ns['visibility'] != 'public' and ns['owner'] != owner):
            expected_status = exceptions.NotFound
        self.do_request('delete_namespace_property',
                        expected_status=expected_status,
                        namespace=ns['namespace'],
                        property_name=actual_prop['property']['name'],
                        client=client)


class MetadefV2RbacPropertiesTemplate(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def test_create_property(self):
        """Test add_metadef_property policy."""
        pass

    @abc.abstractmethod
    def test_get_properties(self):
        """Test get_metadef_property policy."""
        pass

    @abc.abstractmethod
    def test_list_properties(self):
        """Test list_metadef_properties policy."""
        pass

    @abc.abstractmethod
    def test_update_properties(self):
        """Test update_metadef_property policy."""
        pass

    @abc.abstractmethod
    def test_delete_properties(self):
        """Test delete_metadef_property policy."""
        pass


class MetadefV2RbacTagsTest(RbacMetadefBase):
    @classmethod
    def setup_clients(cls):
        super(MetadefV2RbacTagsTest, cls).setup_clients()
        if 'project_member' in cls.credentials:
            persona = 'project_member'
            alt_persona = 'project_alt_member'
        elif 'project_reader' in cls.credentials:
            persona = 'project_reader'
            alt_persona = 'project_alt_reader'
        else:
            persona = 'project_admin'
            alt_persona = 'project_alt_admin'
        cls.persona = getattr(cls, 'os_%s' % persona)
        cls.alt_persona = getattr(cls, 'os_%s' % alt_persona)
        cls.project_id = cls.persona.namespaces_client.project_id
        cls.alt_project_id = cls.alt_persona.namespaces_client.project_id
        cls.tags_client = cls.persona.namespace_tags_client

    def create_tags(self, namespace=None, client=None, owner=None,
                    multiple_tags=False, is_admin=True):
        namespace_tags = []
        if is_admin:
            # Create namespace for two different projects
            if not multiple_tags:
                for ns in namespace:
                    alt_client = None
                    if ns['namespace'].startswith(self.alt_project_id):
                        alt_client = \
                            self.os_project_alt_admin.namespace_tags_client
                        client = alt_client
                    if alt_client is None:
                        client = self.os_project_admin.namespace_tags_client
                    tag_name = "tag_of_%s" % (ns['namespace'])
                    namespace_tag = client.create_namespace_tag(
                        ns['namespace'], tag_name=tag_name)

                    tag = {'namespace': ns, 'tag': namespace_tag}
                    namespace_tags.append(tag)
            else:
                tags = [{"name": "tag1"}, {"name": "tag2"}, {"name": "tag3"}]
                for ns in namespace:
                    alt_client = None
                    if ns['namespace'].startswith(self.alt_project_id):
                        alt_client = \
                            self.os_project_alt_admin.namespace_tags_client
                        client = alt_client
                    if alt_client is None:
                        client = self.os_project_admin.namespace_tags_client
                namespace_multiple_tags = client.create_namespace_tags(
                    ns['namespace'], tags=tags)

                multiple_tags = {'namespace': ns,
                                 'tags': namespace_multiple_tags}
                namespace_tags.append(multiple_tags)

        else:
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

        return namespace_tags

    def assertTagsList(self, actual_tag, client, owner=None):
        ns = actual_tag['namespace']
        if owner:
            if (ns['visibility'] != 'public' and ns['owner'] != owner):
                self.do_request('list_namespace_tags',
                                expected_status=exceptions.NotFound,
                                client=client,
                                namespace=ns['namespace'])
            else:
                resp = self.do_request('list_namespace_tags',
                                       expected_status=200,
                                       client=client,
                                       namespace=ns['namespace'])
                self.assertEqual(actual_tag['tag']['name'],
                                 resp['tags'][0]['name'])
        else:
            resp = self.do_request('list_namespace_tags',
                                   expected_status=200,
                                   client=client,
                                   namespace=ns['namespace'])
            self.assertEqual(actual_tag['tag']['name'],
                             resp['tags'][0]['name'])

    def assertTagGet(self, actual_tag, client, owner=None):
        ns = actual_tag['namespace']
        expected_status = 200
        if (ns['visibility'] != 'public' and ns['owner'] != owner):
            expected_status = exceptions.NotFound

        self.do_request('show_namespace_tag',
                        expected_status=expected_status,
                        namespace=ns['namespace'],
                        tag_name=actual_tag['tag']['name'],
                        client=client)

    def assertTagUpdate(self, tag, client, owner):
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

    def assertDeleteTags(self, tag, client, owner=None, multiple_tags=False,
                         is_admin=True):
        if is_admin:
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
        else:
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
                                tag_name=tag['tag']['name'],
                                client=client)


class MetadefV2RbacTagsTemplate(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def test_create_tag(self):
        """Test add_metadef_tag policy."""
        pass

    @abc.abstractmethod
    def test_get_tags(self):
        """Test get_metadef_tag policy."""
        pass

    @abc.abstractmethod
    def test_list_tags(self):
        """Test list_metadef_tags policy."""
        pass

    @abc.abstractmethod
    def test_update_tags(self):
        """Test update_metadef_tag policy."""
        pass

    @abc.abstractmethod
    def test_delete_tags(self):
        """Test delete_metadef_tag policy."""
        pass
