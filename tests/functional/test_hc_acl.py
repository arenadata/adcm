import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_subdirs_as_parameters

cases, ids = get_data_subdirs_as_parameters(__file__, "syntax", "positive")


@pytest.mark.parametrize("bundle", cases, ids=ids)
def test_posite_upload(sdk_client_ms: ADCMClient, bundle):
    sdk_client_ms.upload_from_fs(bundle)
    assert True
