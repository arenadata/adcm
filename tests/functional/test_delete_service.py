# pylint: disable=W0611, W0621
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir


def test_delete_service(sdk_client_fs: ADCMClient):
    """If host has NO component, than we can simple remove it from cluster.

    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    service.delete()
