# pylint: disable=W0611, W0621
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils


"""
    name - Name of log. Required
    format - Format of body, json/txt. Required
    path - Path of file on node. Required, if field 'content' is none
    content - Text. Required, if field 'path' is none
    if both fields then we get path, if not storage format field then bundle error
"""
FORMAT_STORAGE = ["json_path", "json_content", 'txt_path', "txt_content"]
FIELD = ['name', 'format', 'storage_type']


@pytest.mark.parametrize("bundle", FIELD)
def test_required_fields(sdk_client_fs: ADCMClient, bundle):
    """Task should be failed if required field not presented
    """
    stack_dir = utils.get_data_dir(__file__, "required_fields", "no_{}".format(bundle))
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    action_run = cluster.action_run(name='')
    action_run.wait()
    job = action_run.job()
    log_files_list = job.log_files


@pytest.mark.parametrize("bundle", FORMAT_STORAGE)
def test_different_storage_types_with_format(sdk_client_fs: ADCMClient, bundle):
    """Check different combinations of storage and format
    """
    stack_dir = utils.get_data_dir(__file__, bundle)
    bundle = sdk_client_fs.upload_from_fs(stack_dir)
    cluster = bundle.cluster_create(utils.random_string())
    action = cluster.action_run(name='custom_log')
    action.wait()
    job = action.job()
    logs = job.log_list()
    log_files_list = job.log_files


def test_path_and_content(sdk_client_fs: ADCMClient):
    """If path and content presented we need to get path, not content

    :return:
    """
    pass


def test_multiple_equal_pathes(sdk_client_fs: ADCMClient):
    """Check situation when we have path multiple tasks with one file path

    :return:
    """
    pass


def test_multiple_equal_names(sdk_client_fs: ADCMClient):
    """Check situation when we have path multiple tasks with one name

    :return:
    """
    pass


def test_multiple_equal_pathes_and_names(sdk_client_fs: ADCMClient):
    """Check situation when we have path multiple tasks with one file path and name

    :return:
    """
    pass


def test_check_file_content(sdk_client_fs: ADCMClient):
    pass


def test_check_path_content(sdk_client_fs: ADCMClient):
    pass


def test_incorrect_syntax_for_fields(sdk_client_fs: ADCMClient):
    pass
