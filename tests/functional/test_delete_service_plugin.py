from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils


def test_delete_service_plugin(sdk_client_fs: ADCMClient):
    """Check that delete service plugin will delete service
    """
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__))
    cluster = bundle.cluster_create(utils.random_string())
    service = cluster.service_add(name="service")
    task = service.action_run(name='remove_service')
    task.wait()
    assert task.status == 'success', "Current job status {}. Expected: success".format(task.status)
    service_list = cluster.service_list()
    print(service_list)


def test_delete_service_with_import():
    pass


def test_delete_service_with_export():
    pass
