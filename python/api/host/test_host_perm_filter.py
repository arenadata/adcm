import pytest
from rest_framework.test import APIClient


from adcm import settings
from cm import models
from cm.unit_tests import utils
from rbac import models as rbac_models
from rbac.services import user as user_svc, policy as policy_svc
from rbac.upgrade.role import init_roles
from init_db import init


@pytest.fixture
def init_db():
    init()
    init_roles()
    user_svc.create(
        username='user', password='user', first_name='user', last_name='useroff', profile={}
    )


@pytest.fixture
def anon_api_client(init_db):
    client = APIClient()
    return client


@pytest.fixture
def admin_api_client(init_db):
    client = APIClient()
    client.login(username='admin', password='admin')
    return client


@pytest.fixture
def user_api_client(init_db):
    client = APIClient()
    client.login(username='user', password='user')
    return client


@pytest.fixture
def hosts(init_db):
    bundle = utils.gen_bundle()
    provider = utils.gen_provider(bundle=bundle)
    prototype = utils.gen_prototype(bundle, 'host')
    return [
        utils.gen_host(provider=provider, prototype=prototype),
        utils.gen_host(provider=provider, prototype=prototype),
        utils.gen_host(provider=provider, prototype=prototype),
    ]


@pytest.mark.django_db
def test_anon(anon_api_client, hosts):
    result = anon_api_client.get('/api/v1/host/')
    assert result.status_code == 401


@pytest.mark.django_db
def test_admin(admin_api_client, hosts):
    result = admin_api_client.get('/api/v1/host/')
    assert result.status_code == 200
    data = result.json()
    assert len(data) == 3


@pytest.mark.django_db
def test_user_default_role(user_api_client, hosts):
    result = user_api_client.get('/api/v1/host/')
    assert result.status_code == 200
    data = result.json()
    assert len(data) == 3  # default view permission works


@pytest.mark.django_db
def test_user_no_role(user_api_client, hosts):
    user = rbac_models.User.objects.get(username='user')
    default_policy = rbac_models.Policy.objects.get(name='default')

    # remove all default view permissions
    assert user in default_policy.user.all()
    default_policy.user.remove(user)
    default_policy.apply()

    result = user_api_client.get('/api/v1/host/')
    assert result.status_code == 200
    data = result.json()
    assert len(data) == 0


@pytest.mark.django_db
def test_user_exact_role(user_api_client, hosts):
    user = rbac_models.User.objects.get(username='user')
    default_policy = rbac_models.Policy.objects.get(name='default')
    default_policy.user.remove(user)
    default_policy.apply()

    # allow to delete single host
    role = rbac_models.Role.objects.get(name='Remove hosts')
    policy_svc.policy_create('new policy', role=role, object=[hosts[0]], user=[user])

    result = user_api_client.get('/api/v1/host/')
    assert result.status_code == 200
    data = result.json()
    assert len(data) == 1  # here is the only host user could to delete
