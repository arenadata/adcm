from pathlib import Path

from django.conf import settings
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
        self.login()

        Role.objects.create(name="Cluster Administrator", display_name="Cluster Administrator")
        Role.objects.create(name="Provider Administrator", display_name="Provider Administrator")
        Role.objects.create(name="Service Administrator", display_name="Service Administrator")

        self.test_bundle_filename = "test_bundle.tar"
        self.test_bundle_path = Path(
            settings.BASE_DIR,
            "python/audit/tests/files",
            self.test_bundle_filename,
        )

    def login(self):
        res = self.client.post(
            path=reverse("rbac:token"),
            data={"username": self.test_user_username, "password": self.test_user_password},
            content_type="application/json",
        )
        self.client.defaults["Authorization"] = f"Token {res.data['token']}"

    def upload_bundle(self):
        with open(self.test_bundle_path, encoding="utf-8") as f:
            self.client.post(
                path=reverse("upload-bundle"),
                data={"file": f},
            )

    def load_bundle(self):
        return self.client.post(
            path=reverse("load-bundle"),
            data={"bundle_file": self.test_bundle_filename},
        )

    def create_cluster(self, bundle_id: int, cluster_name: str):
        return self.client.post(
            path=reverse("cluster"),
            data={
                "bundle_id": bundle_id,
                "display_name": f"{cluster_name}_display",
                "name": cluster_name,
                "prototype_id": bundle_id,
            },
        )
