# pylint: disable=W0611, W0621
import coreapi
import pytest

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir
from tests.library import errorcodes as err


@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + '/cluster_export')
    bundle_import = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + '/cluster_import')
    cluster = bundle.cluster_create("test")
    cluster_import = bundle_import.cluster_create("cluster_import")
    service = cluster.service_add(name="hadoop")
    cluster_import.bind(service)
    return cluster, service


def test_delete_service_with_with_active_export(cluster):
    """If host has NO component, than we can simple remove it from cluster.
    """
    service = cluster[1]
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        service.delete()
    err.SERVICE_CONFLICT.equal(e)
