"""Common fixtures for the functional tests"""
import pytest
import allure

only_clean_adcm = pytest.mark.parametrize(
    "additional_adcm_init_config",
    [pytest.param({}, id="clean_adcm")],
    indirect=True,
)


@allure.title("Additional ADCM init config")
@pytest.fixture(
    scope="session",
    params=[
        pytest.param({}, id="clean_adcm"),
        pytest.param({"fill_dummy_data": True}, id="adcm_with_dummy_data", marks=[pytest.mark.full]),
    ],
)
def additional_adcm_init_config(request) -> dict:
    """
    Add options for ADCM init.
    Redefine this fixture in the actual project to alter additional options of ADCM initialisation.
    Ex. If this fixture will return {"fill_dummy_data": True}
    then on the init stage dummy objects will be added to ADCM image
    """
    return request.param
