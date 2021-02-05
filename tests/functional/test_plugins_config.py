# pylint: disable=W0611, W0621
import copy

import pytest
from adcm_client.objects import ADCMClient, Bundle
from adcm_pytest_plugin.utils import get_data_dir
from delayed_assert import assert_expectations, expect

INITIAL_CONFIG = {
    "int": 1,
    "float": 1.0,
    "text": """xxx
xxx
""",
    "file": """yyyy
yyyy
""",
    "string": "zzz",
    "json": [
        {"x": "y"},
        {"y": "z"}
    ],
    "map": {
        "one": "two",
        "two": "three"
    },
    "list": [
        "one",
        "two",
        "three"
    ]
}

KEYS = list(INITIAL_CONFIG.keys())

NEW_VALUES = {
    "int": 2,
    "float": 4.0,
    "text": """new new
xxx
""",
    "file": """new new new
yyyy
""",
    "string": "double new",
    "json": [
        {"x": "new"},
        {"y": "z"}
    ],
    "map": {
        "one": "two",
        "two": "new"
    },
    "list": [
        "one",
        "new",
        "three"
    ]
}

INITIAL_CLUSTERS_CONFIG = {
    'first': {
        'config': copy.deepcopy(INITIAL_CONFIG),
        'services': {
            'First': copy.deepcopy(INITIAL_CONFIG),
            'Second': copy.deepcopy(INITIAL_CONFIG)
        }
    },
    'second': {
        'config': copy.deepcopy(INITIAL_CONFIG),
        'services': {
            'First': copy.deepcopy(INITIAL_CONFIG),
            'Second': copy.deepcopy(INITIAL_CONFIG)
        }
    },
    'third': {
        'config': copy.deepcopy(INITIAL_CONFIG),
        'services': {
            'First': copy.deepcopy(INITIAL_CONFIG),
            'Second': copy.deepcopy(INITIAL_CONFIG)
        }
    },
}


CLUSTER_KEYS = list(INITIAL_CLUSTERS_CONFIG.keys())

SERVICE_NAMES = ['First', 'Second']


def assert_cluster_config(bundle: Bundle, statemap: dict):
    for cname, clv in statemap.items():
        actual_cnf = bundle.cluster(name=cname).config()
        expected_cnf = clv['config']
        for k, v in expected_cnf.items():
            expect(
                v == actual_cnf[k],
                'Cluster {} config "{}" is "{}" while expected "{}"'.format(
                    cname, k, str(actual_cnf[k]), str(v)
                )
            )
        for sname, service_expected_cnf in clv['services'].items():
            service_actual_cnf = bundle.cluster(name=cname).service(name=sname).config()
            for k, v in service_expected_cnf.items():
                expect(
                    v == service_actual_cnf[k],
                    'Cluster {} service {} config {} is {} while expected {}'.format(
                        cname, sname, k, str(service_actual_cnf[k]), str(v)
                    )
                )
    assert_expectations()


@pytest.fixture()
def cluster_bundle(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    for name in INITIAL_CLUSTERS_CONFIG:
        cluster = bundle.cluster_create(name)
        cluster.service_add(name='First')
        cluster.service_add(name='Second')
    return bundle


@pytest.fixture(scope="module")
def keys_clusters():
    result = []
    for i, key in enumerate(KEYS):
        result.append((key, CLUSTER_KEYS[i % 3]))
    return result


@pytest.fixture(scope="module")
def keys_clusters_services():
    result = []
    for i, key in enumerate(KEYS):
        result.append((key, CLUSTER_KEYS[i % 3], SERVICE_NAMES[i % 2]))
    return result


def test_cluster_config(cluster_bundle: Bundle, keys_clusters):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_CONFIG)
    assert_cluster_config(cluster_bundle, expected_state)

    for key, cname in keys_clusters:
        cluster = cluster_bundle.cluster(name=cname)
        cluster.action(name='cluster_' + key).run().try_wait()
        expected_state[cname]["config"][key] = NEW_VALUES[key]
        assert_cluster_config(cluster_bundle, expected_state)


def test_cluster_config_from_service(cluster_bundle: Bundle, keys_clusters_services):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_CONFIG)
    assert_cluster_config(cluster_bundle, expected_state)

    for key, cname, sname in keys_clusters_services:
        cluster = cluster_bundle.cluster(name=cname)
        service = cluster.service(name=sname)
        service.action(name='cluster_' + key).run().try_wait()
        expected_state[cname]["config"][key] = NEW_VALUES[key]
        assert_cluster_config(cluster_bundle, expected_state)


def test_service_config_from_cluster_by_name(cluster_bundle: Bundle, keys_clusters_services):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_CONFIG)
    assert_cluster_config(cluster_bundle, expected_state)

    for key, cname, sname in keys_clusters_services:
        cluster = cluster_bundle.cluster(name=cname)
        cluster.action(name='service_name_' + sname + '_' + key).run().try_wait()
        expected_state[cname]["services"][sname][key] = NEW_VALUES[key]
        assert_cluster_config(cluster_bundle, expected_state)


def test_service_config_from_service_by_name(cluster_bundle: Bundle, keys_clusters_services):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_CONFIG)
    assert_cluster_config(cluster_bundle, expected_state)

    for key, cname, sname in keys_clusters_services:
        service = cluster_bundle.cluster(name=cname).service(name=sname)
        service.action(name='service_name_' + sname + '_' + key).run().try_wait()
        expected_state[cname]["services"][sname][key] = NEW_VALUES[key]
        assert_cluster_config(cluster_bundle, expected_state)


def test_another_service_from_service_by_name(cluster_bundle: Bundle, keys_clusters_services):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_CONFIG)
    assert_cluster_config(cluster_bundle, expected_state)

    for key, cname, sname in keys_clusters_services:
        if sname == "Second":
            continue
        second = cluster_bundle.cluster(name=cname).service(name='Second')
        result = second.action(name='service_name_' + sname + '_' + key).run().wait()
        assert result == "failed", "Job expected to be failed"
        assert_cluster_config(cluster_bundle, expected_state)


def test_service_config(cluster_bundle: Bundle, keys_clusters_services):
    expected_state = copy.deepcopy(INITIAL_CLUSTERS_CONFIG)
    assert_cluster_config(cluster_bundle, expected_state)

    for key, cname, sname in keys_clusters_services:
        cluster = cluster_bundle.cluster(name=cname)
        service = cluster.service(name=sname)
        service.action(name='service_' + key).run().try_wait()
        expected_state[cname]["services"][sname][key] = NEW_VALUES[key]
        assert_cluster_config(cluster_bundle, expected_state)


INITIAL_PROVIDERS_CONFIG = {
    'first': {
        'config': copy.deepcopy(INITIAL_CONFIG),
        'hosts': {
            'first_First': copy.deepcopy(INITIAL_CONFIG),
            'first_Second': copy.deepcopy(INITIAL_CONFIG)
        }
    },
    'second': {
        'config': copy.deepcopy(INITIAL_CONFIG),
        'hosts': {
            'second_First': copy.deepcopy(INITIAL_CONFIG),
            'second_Second': copy.deepcopy(INITIAL_CONFIG)
        }
    },
    'third': {
        'config': copy.deepcopy(INITIAL_CONFIG),
        'hosts': {
            'third_First': copy.deepcopy(INITIAL_CONFIG),
            'third_Second': copy.deepcopy(INITIAL_CONFIG)
        }
    },
}

PROVIDERS = list(INITIAL_PROVIDERS_CONFIG.keys())


def sparse_matrix(*vectors):
    lengs = []
    for a in vectors:
        lengs.append(len(a))

    max_lengs_vector_idx = lengs.index(max(lengs))
    for i, _ in enumerate(vectors[max_lengs_vector_idx]):
        tmp = []
        for j, a in enumerate(vectors):
            tmp.append(a[i % lengs[j]])
        yield tuple(tmp)


def assert_provider_config(bundle: Bundle, statemap: dict):
    for pname, plv in statemap.items():
        actual_cnf = bundle.provider(name=pname).config()
        expected_cnf = plv['config']
        for k, v in expected_cnf.items():
            expect(
                v == actual_cnf[k],
                'Provider {} config "{}" is "{}" while expected "{}"'.format(
                    pname, k, str(actual_cnf[k]), str(v)
                )
            )
        for hname, host_expected_cnf in plv['hosts'].items():
            host_actual_cnf = bundle.provider(name=pname).host(fqdn=hname).config()
            for k, v in host_expected_cnf.items():
                expect(
                    v == host_actual_cnf[k],
                    'Provider {} host {} config {} is {} while expected {}'.format(
                        pname, hname, k, str(host_actual_cnf[k]), str(v)
                    )
                )
    assert_expectations()


@pytest.fixture()
def provider_bundle(sdk_client_fs: ADCMClient):
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
    for name in INITIAL_PROVIDERS_CONFIG:
        provider = bundle.provider_create(name)
        for fqdn in INITIAL_PROVIDERS_CONFIG[name]['hosts']:
            provider.host_create(fqdn=fqdn)
    return bundle


def test_provider_config(provider_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_PROVIDERS_CONFIG)
    assert_provider_config(provider_bundle, expected_state)

    for key, pname in sparse_matrix(KEYS, PROVIDERS):
        provider = provider_bundle.provider(name=pname)
        provider.action(name='provider_' + key).run().try_wait()
        expected_state[pname]["config"][key] = NEW_VALUES[key]

    assert_provider_config(provider_bundle, expected_state)


def test_host_config(provider_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_PROVIDERS_CONFIG)
    assert_provider_config(provider_bundle, expected_state)

    for key, pname, host_idx in sparse_matrix(KEYS, PROVIDERS, [0, 1]):
        provider = provider_bundle.provider(name=pname)
        fqdn = list(INITIAL_PROVIDERS_CONFIG[pname]['hosts'].keys())[host_idx]
        host = provider.host(fqdn=fqdn)
        host.action(name='host_' + key).run().try_wait()
        expected_state[pname]["hosts"][fqdn][key] = NEW_VALUES[key]
        assert_provider_config(provider_bundle, expected_state)


def test_host_config_from_provider(provider_bundle: Bundle):
    expected_state = copy.deepcopy(INITIAL_PROVIDERS_CONFIG)
    assert_provider_config(provider_bundle, expected_state)

    for key, pname, host_idx in sparse_matrix(KEYS, PROVIDERS, [0, 1]):
        provider = provider_bundle.provider(name=pname)
        fqdn = list(INITIAL_PROVIDERS_CONFIG[pname]['hosts'].keys())[host_idx]
        provider.action(name='host_' + key).run(config={"fqdn": fqdn}).try_wait()
        expected_state[pname]["hosts"][fqdn][key] = NEW_VALUES[key]
        assert_provider_config(provider_bundle, expected_state)
