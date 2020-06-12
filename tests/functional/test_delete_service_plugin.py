from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils


def test_delete_service_plugin(sdk_client_fs: ADCMClient):
    """Check that delete service plugin will delete service
    """
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "cluster"))
    cluster = bundle.cluster_create(utils.random_string())
    service = cluster.service_add(name="service")
    task = service.action_run(name='remove_service')
    task.wait()
    assert task.status == 'success', "Current job status {}. Expected: success".format(task.status)
    assert not cluster.service_list()


def test_delete_service_with_import(sdk_client_fs: ADCMClient):
    """Check that possible to delete exported service from cluster
    """
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'export_cluster'))
    bundle_import = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'import_cluster'))
    cluster = bundle.cluster_create("test")
    cluster_import = bundle_import.cluster_create("cluster_import")
    service = cluster.service_add(name="hadoop")
    cluster_import.bind(service)
    task = service.action_run(name='remove_service')
    task.wait()
    assert task.status == 'success', "Current job status {}. Expected: success".format(task.status)
    assert not cluster.service_list()
    assert not cluster_import.service_list()


def test_delete_service_with_export(sdk_client_fs: ADCMClient):
    """Check that possible to delete imported service
    """
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'export_cluster'))
    bundle_import = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'import_cluster'))
    cluster = bundle.cluster_create("test")
    cluster_import = bundle_import.cluster_create("cluster_import")
    service = cluster.service_add(name="hadoop")
    import_service = cluster_import.service_add(name='hadoop')
    import_service.bind(service)
    task = service.action_run(name='remove_service')
    task.wait()
    assert task.status == 'success', "Current job status {}. Expected: success".format(task.status)
    assert not cluster.service_list()
    assert cluster_import.service_list()
    task = import_service.action_run(name='remove_service')
    task.wait()
    assert task.status == 'success', "Current job status {}. Expected: success".format(task.status)
    assert not cluster_import.service_list()
