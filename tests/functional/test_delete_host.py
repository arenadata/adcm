# pylint: disable=W0611, W0621
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir


def test_delete_host(sdk_client_fs: ADCMClient):
    """If host has NO component, than we can simple remove it from cluster.

    :return:
    """
    hostprovider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, '/hostprovider'))
    provider = hostprovider_bundle.provider_create("test")
    host = provider.host_create("test_host")
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__), '/cluster_bundle')
    cluster = bundle.cluster_create("test")
    cluster.service_add(name="zookeeper")
    cluster.host_add(host)
    cluster.host_delete(host)
