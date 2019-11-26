import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_subdirs_as_parameters

cases, ids = get_data_subdirs_as_parameters(__file__, "correct")


@pytest.mark.parametrize("bundle", cases, ids=ids)
def test_upload_one(sdk_client_fs: ADCMClient, bundle):
    sdk_client_fs.upload_from_fs(bundle)
    assert True


def test_upload_all(sdk_client_ms: ADCMClient):
    for c in cases:
        sdk_client_ms.upload_from_fs(c)
    assert True
