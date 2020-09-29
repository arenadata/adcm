from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import random_string

from tests.ui_tests.app.configuration import Configuration


def prepare_cluster_and_get_config(sdk_client: ADCMClient, path, app):
    bundle = sdk_client.upload_from_fs(path)
    cluster_name = "_".join(path.split("/")[-1:] + [random_string()])
    cluster = bundle.cluster_create(name=cluster_name)
    config = Configuration(app.driver,
                           f"{app.adcm.url}/cluster/{cluster.cluster_id}/config")
    return cluster, config
