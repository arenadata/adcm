from adcm_client.objects import ADCMClient, Cluster
from adcm_pytest_plugin.utils import random_string

from tests.ui_tests.app.configuration import Configuration
import allure


def prepare_cluster(sdk_client: ADCMClient, path) -> Cluster:
    bundle = sdk_client.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-1:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    return cluster


@allure.step("Prepare cluster and get config")
def prepare_cluster_and_get_config(sdk_client: ADCMClient, path, app):
    cluster = prepare_cluster(sdk_client, path)
    config = Configuration(app.driver,
                           f"{app.adcm.url}/cluster/{cluster.cluster_id}/config")
    return cluster, config
