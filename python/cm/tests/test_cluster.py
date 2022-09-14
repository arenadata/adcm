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

    def test_cluster_duplicate_name(self):
        new_cluster = Cluster.objects.create(name="new_name", prototype=self.prototype)
        url = reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk})
        response = self.client.patch(
            path=url, data={"name": new_cluster.name}, content_type=APPLICATION_JSON
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")
        self.assertEqual(
            response.json()["desc"], f'Cluster with name "{new_cluster.name}" already exists'
        )
        response = self.client.put(
            path=url, data={"name": new_cluster.name}, content_type=APPLICATION_JSON
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")
        self.assertEqual(
            response.json()["desc"], f'Cluster with name "{new_cluster.name}" already exists'
        )

    def test_cluster_name_validation(self):
        url = reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk})
        valid_names = [
            "letters",
            "all-12 to.ge--the r",
            "Just cluster namE",
            "Another.clus-ter",
            "endswithdigit4",
            "1startswithdigit",
        ]
        invalid_names = [
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

        with self.another_user_logged_in(username="admin", password="admin"):
            for name in valid_names:
                with self.subTest("correct-patch", name=name):
                    response = self.client.patch(
                        path=url, data={"name": name}, content_type=APPLICATION_JSON
                    )
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertEqual(response.json()["name"], name)

                with self.subTest("correct-put", name=name):
                    response = self.client.put(
                        path=url, data={"name": name}, content_type=APPLICATION_JSON
                    )
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertEqual(response.json()["name"], name)

            for name in invalid_names:
                with self.subTest("incorrect-patch", name=name):
                    response = self.client.patch(
                        path=url, data={"name": name}, content_type=APPLICATION_JSON
                    )
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertEqual(response.json()["code"], "WRONG_NAME")

                with self.subTest("incorrect-put", name=name):
                    response = self.client.put(
                        path=url, data={"name": name}, content_type=APPLICATION_JSON
                    )
                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertEqual(response.json()["code"], "WRONG_NAME")
