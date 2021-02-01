from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """ test the users API (public) """

    def setUp(self):
        self.client = APIClient()

    def test_create_valid_user_successful(self):
        """ test creating user with valid payload is successful """

        payload = {
            'email': 'test@gmail.com',
            'password': 'testpw1',
            'name': 'test_name'
        }
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(**res.data)
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_exists(self):
        """ test that creating a user that already exists will fail """
        payload = {
            'email': 'test@gmail.com',
            'password': 'testpw1',
            'name': 'test_name'
        }
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEquals(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """ test that the password must be more than 5 characters """
        payload = {
            'email': 'test1@gmail.com',
            'password': 'short',
            'name': 'test_name'
        }
        res = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()

        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """ test that a token is created for the user """
        payload = {
            'email': 'test@gmail.com',
            'password': 'testpw1'
        }
        create_user(**payload)
        res = self.client.post(TOKEN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('token', res.data)

    def test_create_token_invalid_password(self):
        """ test that token is not created if credentials are invalid """
        create_user(email='test@gmail.com', password='correctpw')
        payload = {
            'email': 'test@gmail.com',
            'password': 'wrongpw'
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('token', res.data)

    def test_create_token_no_user(self):
        """ test that token is not created if user doesn't exist """
        payload = {
            'email': 'invalid@gmail.com',
            'password': 'testpw'
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('token', res.data)

    def test_create_token_missing_field(self):
        """ test that email and pw are both required """
        res = self.client.get(TOKEN_URL, {'email': 'test', 'password': ''})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertNotIn('token', res.data)

    def test_retrieve_user_unauthorized(self):
        """ test that authentication is required for users """
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """ test API requests that require authentication """

    def setUp(self):
        self.user = create_user(
            email='test@gmail.com',
            password='testpw1',
            name='Testname',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """ test retrieving profile for logged in user """
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email,
        })

    def test_post_me_not_allowed(self):
        """ test that POST is not allowed on the me URL """
        res = self.client.post(ME_URL, {})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """ test updating the user profile for authenticated user """
        payload = {'name': 'new name', 'password': 'newpassword1'}

        res = self.client.patch(ME_URL, payload)

        self.user.refresh_from_db()
        self.assertEqual(self.user.name, payload['name'])
        self.assertTrue(self.user.check_password(payload['password']))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
