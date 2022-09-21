import string

from django.urls import reverse
from rest_framework import status

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import Bundle, Cluster, Prototype
from init_db import init


class TestCluster(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        init()

        self.allowed_name_chars_start_end = f"{string.ascii_letters}{string.digits}"
        self.allowed_name_chars_middle = f"{self.allowed_name_chars_start_end}-. _"

        self.valid_names = (
            "letters",
            "all-12 to.ge--t_he r",
            "Just cluster namE",
            "Another.clus-ter",
            "endswithdigit4",
            "1startswithdigit",
            "contains_underscore",
        )
        self.invalid_names = (
            "-starts with hyphen",
            ".starts with dot",
            "_starts with underscore",
            "Ends with hyphen-",
            "Ends with dot.",
            "Ends with underscore_",
        ) + tuple(
            f"forbidden{c}char"
            for c in set(string.punctuation) - set(self.allowed_name_chars_middle)
        )

        self.bundle = Bundle.objects.create()
        self.prototype = Prototype.objects.create(
            name="test_prototype_name", type="cluster", bundle=self.bundle
        )
        self.cluster = Cluster.objects.create(name="test_cluster_name", prototype=self.prototype)

    def test_cluster_update_duplicate_name_fail(self):
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

    def test_cluster_create_duplicate_name_fail(self):
        response = self.client.post(
            path=reverse("cluster"),
            data={"name": self.cluster.name, "prototype_id": self.cluster.prototype.pk},
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "CLUSTER_CONFLICT")
        self.assertEqual(
            response.json()["desc"], f'Cluster with name "{self.cluster.name}" already exists'
        )

    def test_cluster_create_name_validation(self):
        url = reverse("cluster")
        amount_of_clusters = Cluster.objects.count()
        for name in self.invalid_names:
            with self.subTest("invalid", name=name):
                response = self.client.post(
                    path=url,
                    data={"name": name, "prototype_id": self.prototype.pk},
                    content_type=APPLICATION_JSON,
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.json()["code"], "WRONG_NAME")
                self.assertEqual(Cluster.objects.count(), amount_of_clusters)

        for name in self.valid_names:
            with self.subTest("valid", name=name):
                response = self.client.post(
                    path=url,
                    data={"name": name, "prototype_id": self.prototype.pk},
                    content_type=APPLICATION_JSON,
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.json()["name"], name)

    def test_cluster_update_name_validation(self):
        url = reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk})
        with self.another_user_logged_in(username="admin", password="admin"):
            for name in self.valid_names:
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

            for name in self.invalid_names:
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

    def test_cluster_name_update_in_different_states(self):
        state_created = "created"
        state_another = "another state"
        valid_name = self.valid_names[0]
        url = reverse("cluster-details", kwargs={"cluster_id": self.cluster.pk})

        self.cluster.state = state_created
        self.cluster.save()

        with self.another_user_logged_in(username="admin", password="admin"):
            for method in ("patch", "put"):
                response = getattr(self.client, method)(
                    path=url, data={"name": valid_name}, content_type=APPLICATION_JSON
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.json()["name"], valid_name)

            self.cluster.state = state_another
            self.cluster.save()

            for method in ("patch", "put"):
                response = getattr(self.client, method)(
                    path=url, data={"name": valid_name}, content_type=APPLICATION_JSON
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
