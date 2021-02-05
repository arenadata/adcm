# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=W0611, W0621, W0404, W0212, C1801
# from adcm_client.mapper import Mapper
import pytest
import yaml
from adcm_client.base import ObjectNotFound, Paging
from adcm_client.objects import ADCMClient, HostList, TaskFailed
from adcm_pytest_plugin.utils import get_data_dir


pytestmark = pytest.mark.skip(reason="ADCM-961 That test group should be moved to adcm-client")


@pytest.fixture(scope='module')
def schema():
    filename = get_data_dir(__file__) + "/schema.yaml"
    with open(filename, 'r') as f:
        return yaml.load(f)


def test_bundle_upload(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster")
    prototype = bundle.cluster_prototype()

    assert bundle.name == "azaza_cluster"
    assert bundle.description == "That is description"
    assert bundle.version == "1.4"
    assert prototype.name == "azaza_cluster"
    assert prototype.description == "That is description"
    assert prototype.version == "1.4"


def test_bundle_delete(sdk_client_fs: ADCMClient):
    with pytest.raises(ObjectNotFound):
        sdk_client_fs.bundle_delete(name="unicorn")
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster")
    sdk_client_fs.bundle_delete(name=bundle.name)


def test_bundle_test_list(sdk_client_fs: ADCMClient):
    for i in range(1, 4):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster" + str(i))
    type1 = sdk_client_fs.bundle_list(name="cluster_type_1")
    assert len(type1) == 2
    assert type1[0].name == "cluster_type_1"
    assert type1[1].name == "cluster_type_1"
    assert ((type1[0].version == "1.4" and type1[1].version == "1.5") or (
            type1[0].version == "1.5" and type1[1].version == "1.4"))


def _assert_attrs(obj):
    # assert dict(obj._data).items() <= obj.__dict__.items()
    missed = []
    for k in obj._data.keys():
        if not hasattr(obj, k):
            missed.append(k)
    assert missed == []


def test_cluster_attrs(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster")
    cluster1 = bundle.cluster_prototype().cluster_create(name="sample cluster")
    _assert_attrs(cluster1)


def test_cluster_crud(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster")
    cluster1 = bundle.cluster_prototype().cluster_create(name="sample cluster")
    cluster2 = bundle.cluster_create(name="sample cluster 2", description="huge one!")

    assert cluster1.cluster_id == 1
    assert cluster1.name == "sample cluster"
    assert cluster2.cluster_id == 2
    assert cluster2.name == "sample cluster 2"

    cl = bundle.cluster_list()
    assert len(cl) == 2
    assert cl[0].name != cl[1].name

    assert len(bundle.cluster_list(name="sample cluster")) == 1

    cluster1.delete()
    cl = bundle.cluster_list()
    assert len(cl) == 1
    assert cl[0].description == cluster2.description

    cluster2.delete()
    assert bundle.cluster_list() == []


def test_hostprovider_and_host_crud(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/provider")
    provider = bundle.provider_prototype().provider_create(name="azaza")
    _assert_attrs(provider)
    _assert_attrs(provider.prototype())
    assert provider.provider_id == 1
    assert provider.name == "azaza"
    host = provider.host_create(fqdn="localhost")
    _assert_attrs(host)
    _assert_attrs(host.prototype())
    host.delete()
    provider.delete()


def test_cluster_action(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster")
    cluster = bundle.cluster_create(name="sample cluster")
    install = cluster.action(name="install")
    assert install.name == "install"
    _assert_attrs(install)
    job = install.run()
    assert job.wait() == "success"


def test_cluster_config(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster")
    cluster = bundle.cluster_create(name="sample cluster")
    conf1 = cluster.config()
    assert conf1['xxx']['yyy'] == 'hahaha'
    conf1['xxx']['yyy'] = 'bimba'
    result = cluster.config_set(conf1)
    conf2 = cluster.config()
    assert conf2['xxx']['yyy'] == 'bimba'
    assert result == conf2


def test_cluster_full_config(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(
        get_data_dir(__file__) + "/cluster_with_activatable")
    cluster = bundle.cluster_create(name="sample cluster")
    conf1 = cluster.config(full=True)
    assert conf1['config']['xxx']['yyy'] == 'hahaha'
    conf1['config']['xxx']['yyy'] = 'bimba'
    result = cluster.config_set(conf1)
    conf2 = cluster.config(full=True)
    assert conf2['config']['xxx']['yyy'] == 'bimba'
    assert result == conf2


def test_cluster_config_attrs(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(
        get_data_dir(__file__) + "/cluster_with_activatable")
    cluster = bundle.cluster_create(name="sample cluster")
    conf3 = cluster.config(full=True)
    conf3['attr']['xxx']['active'] = False
    cluster.config_set(conf3)
    conf4 = cluster.config(full=True)
    assert conf3['attr']['xxx']['active'] == conf4['attr']['xxx']['active']


def test_cluster_set_diff(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster")
    cluster = bundle.cluster_create(name="sample cluster")
    cluster.config_set_diff({'xxx': {'yyy': 'bimba'}})
    conf1 = cluster.config(full=True)
    assert conf1['config']['xxx']['yyy'] == 'bimba'


def test_cluster_service(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster_with_service")
    cluster = bundle.cluster_create(name="sample cluster")
    service = cluster.service_add(name="ahaha_service")
    _assert_attrs(service)
    _assert_attrs(service.prototype())
    service.action(name="install").run().wait()


@pytest.fixture()
def cluster_with_service(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster_with_service")
    cluster = bundle.cluster_create(name="sample cluster")
    cluster.service_add(name="ahaha_service")
    return cluster


def test_hostcomponent(sdk_client_fs: ADCMClient, cluster_with_service):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/provider")
    provider = bundle.provider_prototype().provider_create(name="azaza")
    host1 = provider.host_create(fqdn="localhost1")
    host2 = provider.host_create(fqdn="localhost2")
    host3 = provider.host_create(fqdn="localhost3")
    cluster_with_service.host_add(host1)
    cluster_with_service.host_add(host2)
    cluster_with_service.host_add(host3)
    service = cluster_with_service.service(name="ahaha_service")
    components = service.component_list()
    cluster_with_service.hostcomponent_set(
        (host1, components[0]),
        (host2, components[0]),
        (host3, components[0]),
        (host3, components[1]),
    )


def test_cluster_service_not_found(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster_with_service")
    cluster = bundle.cluster_create(name="sample cluster")
    with pytest.raises(ObjectNotFound):
        cluster.service(name="ahaha_service")
    cluster.service_add(name="ahaha_service")
    assert cluster.service().name == "ahaha_service"


def test_cluster_binding(sdk_client_fs: ADCMClient):
    pass
    # b_export = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster_with_export")
    # b_import = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster_with_import")
    # exporter = b_export.cluster_create("exporter")
    # exporter.service_add(name="service")
    # importer = b_import.cluster_create("importer")
    # importer.bind(exporter)
    # assert len(importer.bind_list()) == 1
    # importer.bind(exporter.service(name="service"))
    # assert len(importer.bind_list()) == 2


def test_action_fail(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster_with_fail")
    cluster = bundle.cluster_create(name="sample cluster")
    with pytest.raises(TaskFailed):
        cluster.action_run(name="fail").try_wait()


def test_cluster_upgrade(sdk_client_fs: ADCMClient):
    for i in range(1, 4):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/cluster_upgrade" + str(i))

    cluster = sdk_client_fs.bundle(name='cluster', version="1.4").cluster_create(name="azaza")
    assert len(cluster.upgrade_list()) == 2
    _assert_attrs(cluster.upgrade(name="2"))
    cluster.upgrade(name="2").do()
    assert len(cluster.upgrade_list()) == 1
    cluster.upgrade(name="3").do()
    assert len(cluster.upgrade_list()) == 0


def test_paging_on_hosts(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__) + "/provider")
    provider = bundle.provider_prototype().provider_create(name="azaza")
    for i in range(1, 100):
        provider.host_create(fqdn='host{}'.format(str(i)))

    prev_id = -1
    prev_fqdn = 'xxxx'
    for host in Paging(provider.host_list):
        assert host.provider_id == provider.provider_id
        assert host.fqdn != prev_fqdn
        assert host.id != prev_id
        prev_id = host.id
        prev_fqdn = host.fqdn

    prev_id = -1
    prev_fqdn = 'xxxx'
    for host in Paging(HostList, api=provider._api):
        assert host.provider_id == provider.provider_id
        assert host.fqdn != prev_fqdn
        assert host.id != prev_id
        prev_id = host.id
        prev_fqdn = host.fqdn


def test_adcm_config_url(sdk_client_fs: ADCMClient):
    sdk_client_fs.adcm().config_set_diff({"global": {"adcm_url": sdk_client_fs.url}})
    conf = sdk_client_fs.adcm().config()
    assert conf["global"]["adcm_url"] == sdk_client_fs.url


def test_adcm_config_url_guess(sdk_client_fs: ADCMClient):
    conf = sdk_client_fs.adcm().config()
    assert conf["global"]["adcm_url"] == sdk_client_fs.url


def test_adcm_config_url_no_guess(sdk_client_fs: ADCMClient):
    sdk_client_fs.adcm().config_set_diff({"global": {"adcm_url": "azaza"}})
    sdk_client_fs.guess_adcm_url()
    conf = sdk_client_fs.adcm().config()
    assert conf["global"]["adcm_url"] == "azaza"


# def test_mapper(sdk_client_fs: ADCMClient):
#    Mapper(get_data_dir(__file__) + '/mapper.yaml', sdk_client_fs).do()
