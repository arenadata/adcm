from django.test import Client, TestCase
from django.urls import reverse

from rbac.models import Role, User


class BaseTestCase(TestCase):
    def setUp(self) -> None:
        self.test_user_username = "test_user"
        self.test_user_password = "test_user_password"

        self.test_user = User.objects.create_user(
            username=self.test_user_username,
            password=self.test_user_password,
            is_superuser=True,
        )

        self.client = Client(HTTP_USER_AGENT='Mozilla/5.0')
        self._login()

        Role.objects.create(name="Cluster Administrator", display_name="Cluster Administrator")
        Role.objects.create(name="Provider Administrator", display_name="Provider Administrator")
        Role.objects.create(name="Service Administrator", display_name="Service Administrator")

    def _login(self):
        res = self.client.post(
            path=reverse("rbac:token"),
            data={"username": self.test_user_username, "password": self.test_user_password},
            content_type="application/json",
        )
        self.client.defaults["Authorization"] = f"Token {res.data['token']}"
