"""
ADSS prod image tests
"""
import allure

pytestmark = [
    allure.suite("Production image content tests"),
    allure.link("https://arenadata.atlassian.net/browse/ADSS-299"),
]


PROD_CLUSTER_TYPES = ["ADB"]
PROD_HANDLERS = ["ADB-backup-handler", "ADB-restore-handler"]
PROD_RESOURCE_TYPES = ["backups", "restores"]


def test_include_only_prod_objects(adss_client_fs):
    """
    Test include only prod objects in prod image
    """
    cluster_types = [c_type.name for c_type in adss_client_fs.cluster_type_iter()]
    assert PROD_CLUSTER_TYPES == cluster_types, "Current Cluster Types not equal prod"

    handlers = [handler.name for handler in adss_client_fs.handler_iter()]
    assert PROD_HANDLERS == handlers, "Current Handlers not equal prod"

    resource_types = [r_type.name for r_type in adss_client_fs.resource_type_iter()]
    assert PROD_RESOURCE_TYPES == resource_types, "Current Resource Types not equal prod"
