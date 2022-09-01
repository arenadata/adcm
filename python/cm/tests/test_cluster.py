from django.urls import reverse
from rest_framework import status

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import Bundle, Cluster, Prototype
from init_db import init


class TestCluster(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        init()

        self.bundle = Bundle.objects.create()
        self.prototype = Prototype.objects.create(
            name="test_prototype_name", type="cluster", bundle=self.bundle
        )
        self.cluster = Cluster.objects.create(name="test_cluster_name", prototype=self.prototype)

    def test_cluster_name_validation(self):
        self.login("admin", "admin")
        url = reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk})

        valid_names = ["letters", "all-12 to.ge--the r", "Just cluster namE", "Another.clus-ter"]
        invalid_names = [
            "1starts with digit",
            "-starts with hyphen",
            ".starts with dot",
            "Ends with hyphen-",
            "Ends with dot.",
            "Use-forbidden_chars",
            "Use-forbidden[chars",
            "Use-forbidden&chars",
            "Use-forbidden?chars",
            "Use-forbidden!chars",
        ]

        for name in valid_names:
            response = self.client.patch(
                path=url, data={"name": name}, content_type=APPLICATION_JSON
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["name"] == name

            response = self.client.put(path=url, data={"name": name}, content_type=APPLICATION_JSON)
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["name"] == name

        for name in invalid_names:
            response = self.client.patch(
                path=url, data={"name": name}, content_type=APPLICATION_JSON
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "name" in response.json()

            response = self.client.put(path=url, data={"name": name}, content_type=APPLICATION_JSON)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "name" in response.json()
