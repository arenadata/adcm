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
# pylint: disable=R0901, R0904
from adcm_client.wrappers.api import ADCMApiWrapper
from adcm_client.util import stream
from contextlib import contextmanager
from .base import strip_none_keys, BaseAPIObject, BaseAPIListObject, ObjectNotFound, ADCMApiError

# If we are running the client from tests with Allure we expected that code
# to trace steps in Allure UI.
# But in case of running client outside of testing Allure is useless in virtualenv.
# So that code should be flexible enought to work with Allure or without.
ALLURE = True
try:
    import allure
except ImportError:
    ALLURE = False


# That is trick which is allmost the same that in _allure.py::StepContext
# We have a function that can be used as contextmanager and decorator
# in same time.
@contextmanager
def dummy_context(text):
    yield text


def allure_step(text):
    if ALLURE:
        return allure.step(text)
    return dummy_context(text)


class NoCredentionsProvided(Exception):
    """There is no user/password provided. It was not passsed as init parameters
    during ADCMClient initialization and was not passed as a parameter to auth()
    function
    """


##################################################
#                 B U N D L E S
##################################################
class IncorrectPrototypeType(Exception):
    pass


class Bundle(BaseAPIObject):
    IDNAME = "bundle_id"
    PATH = ["stack", "bundle"]
    FILTERS = ["name", "version"]

    id = None
    bundle_id = None
    name = None
    description = None
    version = None

    def provider_prototype(self) -> "ProviderPrototype":
        return self._child_obj(ProviderPrototype)

    def provider_create(self, name, description=None) -> "Provider":
        try:
            prototype = self.provider_prototype()
        except ObjectNotFound:
            raise IncorrectPrototypeType
        return prototype.provider_create(name, description)

    def provider_list(self, paging=None, **args) -> "ProviderList":
        try:
            prototype = self.provider_prototype()
        except ObjectNotFound:
            raise IncorrectPrototypeType
        return prototype.provider_list(paging=paging, **args)

    def provider(self, **args) -> "Provider":
        try:
            prototype = self.provider_prototype()
        except ObjectNotFound:
            raise IncorrectPrototypeType
        return prototype.provider(**args)

    def service_prototype(self, **args) -> "ServicePrototype":
        return self._child_obj(ServicePrototype, **args)

    def cluster_prototype(self) -> "ClusterPrototype":
        return self._child_obj(ClusterPrototype)

    def cluster_create(self, name, description=None) -> "Cluster":
        try:
            prototype = self.cluster_prototype()
        except ObjectNotFound:
            raise IncorrectPrototypeType
        return prototype.cluster_create(name, description)

    def cluster_list(self, paging=None, **args) -> "ClusterList":
        try:
            prototype = self.cluster_prototype()
        except ObjectNotFound:
            raise IncorrectPrototypeType
        return prototype.cluster_list(paging=paging, **args)

    def cluster(self, **args) -> "Cluster":
        try:
            prototype = self.cluster_prototype()
        except ObjectNotFound:
            raise IncorrectPrototypeType
        return prototype.cluster(**args)


class BundleList(BaseAPIListObject):
    _ENTRY_CLASS = Bundle


##################################################
#              P R O T O T Y P E
##################################################
class Prototype(BaseAPIObject):
    PATH = ["stack", "prototype"]
    IDNAME = "prototype_id"
    FILTERS = ["name", "bundle_id"]

    id = None
    prototype_id = None
    name = None
    type = None
    description = None
    version = None
    bundle_id = None
    config = None
    actions = None
    url = None

    def bundle(self) -> "Bundle":
        return self._parent_obj(Bundle)


class PrototypeList(BaseAPIListObject):
    _ENTRY_CLASS = Prototype


class ClusterPrototype(Prototype):
    PATH = ["stack", "cluster"]
    FILTERS = ["name", "bundle_id"]

    def cluster_create(self, name, description=None) -> "Cluster":
        if self.type != 'cluster':
            raise IncorrectPrototypeType
        return new_cluster(
            self._api,
            prototype_id=self.prototype_id,
            name=name,
            description=description
        )

    def cluster_list(self, paging=None, **args) -> "ClusterList":
        return self._child_obj(ClusterList, paging=paging, **args)

    def cluster(self, **args) -> "Cluster":
        return self._child_obj(Cluster, **args)


class ClusterPrototypeList(BaseAPIListObject):
    _ENTRY_CLASS = ClusterPrototype


class ServicePrototype(Prototype):
    PATH = ["stack", "service"]
    FILTERS = ["name", "bundle_id"]

    shared = None
    display_name = None
    required = None
    shared = None
    components = None
    exports = None
    imports = None
    monitoring = None

    def service_list(self, paging=None, **args) -> "ServiceList":
        return self._child_obj(ServiceList, paging=paging, **args)

    def service(self, **args) -> "Service":
        return self._child_obj(Service)


class ServicePrototypeList(BaseAPIListObject):
    _ENTRY_CLASS = ServicePrototype


class ProviderPrototype(Prototype):
    PATH = ["stack", "provider"]
    FILTERS = ["name", "bundle_id"]

    display_name = None
    required = None
    upgrade = None

    def provider_create(self, name, description=None) -> "Provider":
        if self.type != 'provider':
            raise IncorrectPrototypeType
        return new_provider(
            self._api,
            prototype_id=self.prototype_id,
            name=name,
            description=description
        )

    def provider_list(self, paging=None, **args) -> "ProviderList":
        return self._child_obj(ProviderList, paging=paging, **args)

    def provider(self, **args) -> "Provider":
        return self._child_obj(Provider, **args)


class ProviderPrototypeList(BaseAPIListObject):
    _ENTRY_CLASS = ProviderPrototype


class HostPrototype(Prototype):
    PATH = ["stack", "host"]
    FILTERS = ["name", "bundle_id"]

    display_name = None
    required = None
    monitoring = None

    def host_list(self, paging=None, **args) -> "HostList":
        return self._child_obj(HostList, paging=paging, **args)

    def host(self, **args) -> "Host":
        return self._child_obj(Host, **args)


class HostPrototypeList(BaseAPIListObject):
    _ENTRY_CLASS = HostPrototype


##################################################
#           B A S E  O B J E C T
##################################################
class _BaseObject(BaseAPIObject):
    id = None
    url = None
    state = None
    prototype_id = None
    issue = None
    button = None

    def prototype(self):
        raise NotImplementedError

    def action(self, **args) -> "Action":
        return self._subobject(Action, **args)

    def action_list(self, paging=None, **args) -> "ActionList":
        return self._subobject(ActionList, paging=paging, **args)

    def action_run(self, **args) -> "Task":
        action = self.action(**args)
        return action.run()

    def config(self, full=False):
        history_entry = self._subcall("config", "current", "list")
        if full:
            return history_entry
        return history_entry['config']

    @allure_step("Save config")
    def config_set(self, data):
        if "config" in data and "attr" in data:
            # We are in a new mode with full_info == True
            if data["attr"] is None:
                data["attr"] = []
            history_entry = self._subcall(
                'config', 'history', 'create',
                config=data["config"],
                attr=data["attr"],
            )
            return history_entry
        history_entry = self._subcall('config', 'history', 'create', config=data)
        return history_entry['config']

    @allure_step("Save config")
    def config_set_diff(self, data):
        config = self.config()
        for gk, gv in data.items():
            if isinstance(gv, dict):
                for k, v in gv.items():
                    config[gk][k] = v
            else:
                config[gk] = v
        self.config_set(config)

    def config_prototype(self):
        return self.prototype().config


##################################################
#              P R O V I D E R
##################################################
class Provider(_BaseObject):
    IDNAME = "provider_id"
    PATH = ["provider"]
    FILTERS = ["name", "prototype_id"]
    provider_id = None
    name = None
    description = None
    bundle_id = None

    def bundle(self) -> "Bundle":
        return self._parent_obj(Bundle)

    def host_create(self, fqdn) -> "Host":
        return new_host(self._api, **self._merge(fqdn=fqdn))

    def host_list(self, paging=None, **args) -> "HostList":
        return self._child_obj(HostList, paging=paging, **args)

    def host(self, **args) -> "Host":
        return self._child_obj(Host, **args)

    def prototype(self) -> "ProviderPrototype":
        return self._parent_obj(ProviderPrototype)

    def upgrade(self, **args) -> "Upgrade":
        return self._subobject(Upgrade, **args)

    def upgrade_list(self, paging=None, **args) -> "UpgradeList":
        return self._subobject(UpgradeList, paging=paging, **args)


class ProviderList(BaseAPIListObject):
    _ENTRY_CLASS = Provider


@allure_step('Create provider {name}')
def new_provider(api, **args) -> "Provider":
    p = api.objects.provider.create(**strip_none_keys(args))
    return Provider(api, provider_id=p['id'])


##################################################
#              C L U S T E R
##################################################
class Cluster(_BaseObject):
    IDNAME = "cluster_id"
    PATH = ["cluster"]
    FILTERS = ["name", "prototype_id"]
    cluster_id = None
    name = None
    description = None
    bundle_id = None
    serviceprototype = None
    status = None

    def prototype(self) -> "ClusterPrototype":
        return self._parent_obj(ClusterPrototype)

    def bind(self, target):
        if isinstance(target, Cluster):
            self._subcall("bind", "create", export_cluster_id=target.cluster_id)
        elif isinstance(target, Service):
            self._subcall("bind", "create", export_cluster_id=target.cluster_id,
                          export_service_id=target.service_id)
        else:
            raise NotImplementedError

    def bind_list(self, paging=None):
        return self._subcall("bind", "list")

    def bundle(self) -> "Bundle":
        proto = self.prototype()
        return proto.bundle()

    def button(self):
        raise NotImplementedError

    def host(self, **args) -> "Host":
        return self._child_obj(Host, **args)

    def host_list(self, paging=None, **args) -> "HostList":
        return self._child_obj(HostList, paging=paging, **args)

    def host_add(self, host: "Host") -> "Host":
        with allure_step("Add host {} to cluster {}".format(host.fqdn, self.name)):
            data = self._subcall("host", "create", host_id=host.id)
            return Host(self._api, id=data['id'])

    def host_delete(self, host: "Host"):
        with allure_step("Remove host {} from cluster {}".format(host.fqdn, self.name)):
            self._subcall("host", "delete", host_id=host.id)

    def service(self, **args) -> "Service":
        return self._subobject(Service, **args)

    def service_list(self, paging=None, **args) -> "ServiceList":
        return self._subobject(ServiceList, paging=paging, **args)

    def service_add(self, **args) -> "Service":
        proto = self.bundle().service_prototype(**args)
        with allure_step("Add service {} to cluster {}".format(proto.name, self.name)):
            data = self._subcall("service", "create", prototype_id=proto.id)
            return self._subobject(Service, service_id=data['id'])

#    @allure_step("Remove service to cluster")
#    def service_delete(self, service):
#        self._subcall("service", "delete", service_id=service.id)

    def hostcomponent(self):
        return self._subcall("hostcomponent", "list")

    @allure_step("Save hostcomponents map")
    def hostcomponent_set(self, *hostcomponents):
        hc = []
        for i in hostcomponents:
            h, c = i
            hc.append({
                'host_id': h.id,
                'service_id': c.service_id,
                'component_id': c.id
            })
        return self._subcall("hostcomponent", "create", hc=hc)

    def status_url(self):
        return self._subcall("status", "list")

    def imports(self):
        raise NotImplementedError

    def issue(self):
        raise NotImplementedError

    def upgrade(self, **args) -> "Upgrade":
        return self._subobject(Upgrade, **args)

    def upgrade_list(self, paging=None, **args) -> "UpgradeList":
        return self._subobject(UpgradeList, paging=paging, **args)


class ClusterList(BaseAPIListObject):
    _ENTRY_CLASS = Cluster


@allure_step('Create cluster {name}')
def new_cluster(api: ADCMApiWrapper, **args) -> "Cluster":
    c = api.objects.cluster.create(**strip_none_keys(args))
    return Cluster(api, cluster_id=c['id'])


##################################################
#          U P G R A D E
##################################################
class Upgrade(BaseAPIObject):
    IDNAME = "upgrade_id"
    PATH = None
    SUBPATH = ["upgrade"]

    id = None
    upgrade_id = None
    url = None
    name = None
    description = None
    min_version = None
    max_version = None
    min_strict = None
    max_strict = None
    upgradable = None
    state_available = None
    state_on_success = None

    def do(self, **args):
        with allure_step("Do upgrade {}".format(self.name)):
            self._subcall("do", "create", **args)


class UpgradeList(BaseAPIListObject):
    SUBPATH = ["upgrade"]
    _ENTRY_CLASS = Upgrade


##################################################
#           S E R V I C E S
##################################################
class Service(_BaseObject):
    IDNAME = "service_id"
    PATH = None
    SUBPATH = ["service"]

    id = None
    service_id = None
    bundle_id = None
    name = None
    description = None
    display_name = None
    cluster_id = None
    status = None
    button = None
    monitoring = None

    def bind(self, target):
        if isinstance(target, Cluster):
            self._subcall("bind", "create", export_cluster_id=target.cluster_id)
        elif isinstance(target, Service):
            self._subcall("bind", "create", export_cluster_id=target.cluster_id,
                          export_service_id=target.service_id)
        else:
            raise NotImplementedError

    def prototype(self) -> "ServicePrototype":
        return ServicePrototype(self._api, id=self.prototype_id)

    def imports(self):
        raise NotImplementedError

    def bind_list(self, paging=None):
        return self._subcall("bind", "list")

    def component(self, **args) -> "Component":
        return self._subobject(Component, **args)

    def component_list(self, paging=None, **args) -> "ComponentList":
        return self._subobject(ComponentList, paging=paging, **args)


class ServiceList(BaseAPIListObject):
    SUBPATH = ["service"]
    _ENTRY_CLASS = Service


##################################################
#           C O M P O N E N T S
##################################################
class Component(BaseAPIObject):
    IDNAME = "component_id"
    SUBPATH = ["component"]

    id = None
    component_id = None
    name = None
    display_name = None
    description = None
    constraint = None
    params = None

    @property
    def service_id(self):
        return self._endpoint.path_args["service_id"]


class ComponentList(BaseAPIListObject):
    SUBPATH = ["component"]
    _ENTRY_CLASS = Component


##################################################
#              H O S T
##################################################
class Host(_BaseObject):
    IDNAME = "host_id"
    PATH = ["host"]
    FILTERS = ["fqdn", "prototype_id", "provider_id", "cluster_id"]

    id = None
    host_id = None
    fqdn = None
    provider_id = None
    cluster_id = None
    description = None
    bundle_id = None
    status = None

    def provider(self) -> "Provider":
        return self._parent_obj(Provider)

    def cluster(self) -> "Cluster":
        return self._parent_obj(Cluster)

    def bundle(self) -> "Bundle":
        return self._parent_obj(Bundle)

    def prototype(self) -> "HostPrototype":
        return self._parent_obj(HostPrototype)


class HostList(BaseAPIListObject):
    _ENTRY_CLASS = Host


@allure_step('Create host {fqdn}')
def new_host(api, **args) -> "Host":
    h = api.objects.provider.host.create(**args)
    return Host(api, host_id=h['id'])


##################################################
#              A C T I O N
##################################################
class Action(BaseAPIObject):
    IDNAME = "action_id"
    PATH = None
    SUBPATH = ["action"]
    FILTERS = ["name"]

    action_id = None
    button = None
    id = None
    name = None
    display_name = None
    description = None
    params = None
    prototype_id = None
    required_hostcomponentmap = None
    hostcomponentmap = None
    script = None
    script_type = None
    state_available = None
    state_on_fail = None
    state_on_success = None
    type = None
    url = None

    def config(self):
        raise NotImplementedError

    def log_files(self):
        raise NotImplementedError

    def task(self, **args) -> "Task":
        return self._child_obj(Task, **args)

    def task_list(self, **args) -> "TaskList":
        return self._child_obj(TaskList, **args)

    def run(self, **args) -> "Task":
        with allure_step("Run action {}".format(self.name)):
            data = self._subcall("run", "create", **args)
            return Task(self._api, task_id=data["id"])


class ActionList(BaseAPIListObject):
    SUBPATH = ["action"]
    _ENTRY_CLASS = Action


##################################################
#              T A S K
##################################################
class TaskFailed(Exception):
    pass


class Task(BaseAPIObject):
    IDNAME = "task_id"
    PATH = ["task"]
    FILTERS = ['action_id', 'pid', 'status', 'start_date', 'finish_date']
    _END_STATUSES = ["failed", "success"]
    action = None
    action_id = None
    config = None
    hostcomponentmap = None
    task_id = None
    id = None
    jobs = None
    pid = None
    selector = None
    status = None
    url = None

    def job(self, **args) -> "Job":
        return Job(self._api, path_args=dict(task_id=self.id), **args)

    def job_list(self, paging=None, **args) -> "JobList":
        return JobList(self._api, paging=paging, path_args=dict(task_id=self.id), **args)

    @allure_step("Wait for task end")
    def wait(self, timeout=None):
        return self.wait_for_attr("status",
                                  self._END_STATUSES,
                                  timeout=timeout)

    @allure_step("Wait for task to success.")
    def try_wait(self, timeout=None):
        status = self.wait(timeout=timeout)

        if status == "failed":
            for job in self.job_list(status="failed"):
                for file in job.log_files:
                    print(self._api.client.get(file["url"])["content"])
            raise TaskFailed

        return status


class TaskList(BaseAPIListObject):
    _ENTRY_CLASS = Task


##################################################
#              J O B
##################################################
class Job(BaseAPIObject):
    IDNAME = "job_id"
    PATH = ["job"]
    FILTERS = ['action_id', 'task_id', 'pid', 'status', 'start_date', 'finish_date']
    _END_STATUSES = ["failed", "success"]
    _WAIT_INTERVAL = .2
    id = None
    job_id = None
    pid = None
    status = None
    url = None
    log_files = None
    task_id = None

    def __init__(self, api: ADCMApiWrapper, path=None, path_args=None, **args):
        super().__init__(api, path, **args)

    def wait(self, timeout=None):
        return self.wait_for_attr("status",
                                  self._END_STATUSES,
                                  timeout=timeout)


class JobList(BaseAPIListObject):
    _ENTRY_CLASS = Job


##################################################
#              A D C M
##################################################
class ADCM(BaseAPIObject):
    IDNAME = "adcm_id"
    PATH = ["adcm"]
    id = None
    name = None
    prototype_id = None
    url = None
    prototype_version = None
    bundle_id = None

    # TODO: Remove that function when it become first class object
    def config(self, full=False):
        history_entry = self._subcall("config", "current", "list")
        if full:
            return history_entry
        return history_entry['config']

    @allure_step("Save config")
    def config_set(self, data):
        if "config" in data and "attr" in data:
            # We are in a new mode with full_info == True
            if data["attr"] is None:
                data["attr"] = []
            history_entry = self._subcall(
                'config', 'history', 'create',
                config=data["config"],
                attr=data["attr"],
            )
            return history_entry
        history_entry = self._subcall('config', 'history', 'create', config=data)
        return history_entry['config']

    @allure_step("Save config")
    def config_set_diff(self, data):
        config = self.config()
        for gk, gv in data.items():
            if isinstance(gv, dict):
                for k, v in gv.items():
                    config[gk][k] = v
            else:
                config[gk] = v
        self.config_set(config)

    def config_prototype(self):
        return self.prototype().config


##################################################
#              C L I E N T
##################################################
class ADCMClient:
    def __init__(self, api=None, url=None, user=None, password=None):
        if api is not None:
            self._api = api
            self.url = api.url
            if self.api_token() is None:
                self.auth(user, password)
        else:
            self.url = url
            self._api = ADCMApiWrapper(self.url)
            self.auth(user, password)
        if self.api_token() is not None:
            self.guess_adcm_url()

    def auth(self, user=None, password=None):
        if user is None or password is None:
            raise NoCredentionsProvided
        self._api.auth(user, password)
        if self.api_token() is None:
            raise ADCMApiError("Incorrect user/password. Unable to auth.")

    def api_token(self):
        return self._api.api_token

    def adcm(self) -> ADCM:
        return ADCM(self._api)

    def guess_adcm_url(self):
        config = self.adcm().config()
        if config['global']['adcm_url'] is None:
            self.adcm().config_set_diff({"global": {"adcm_url": self.url}})

    def bundle(self, **args) -> Bundle:
        return Bundle(self._api, **args)

    def bundle_list(self, paging=None, **args) -> BundleList:
        return BundleList(self._api, paging=paging, **args)

    def cluster(self, **args) -> Cluster:
        return Cluster(self._api, **args)

    def cluster_list(self, paging=None, **args) -> ClusterList:
        return ClusterList(self._api, paging=paging, **args)

    def cluster_prototype(self, **args) -> ClusterPrototype:
        return ClusterPrototype(self._api, **args)

    def cluster_prototype_list(self, paging=None, **args) -> ClusterPrototypeList:
        return ClusterPrototypeList(self._api, paging=paging, **args)

    def host(self, **args) -> Host:
        return Host(self._api, **args)

    def host_list(self, paging=None, **args) -> HostList:
        return HostList(self._api, paging=paging, **args)

    def host_prototype(self, **args) -> HostPrototype:
        return HostPrototype(self._api, **args)

    def host_prototype_list(self, paging=None, **args) -> HostPrototypeList:
        return HostPrototypeList(self._api, paging=paging, **args)

    def job(self, **args) -> Job:
        return Job(self._api, **args)

    def job_list(self, paging=None, **args) -> JobList:
        return JobList(self._api, paging=paging, **args)

    def prototype(self, **args) -> Prototype:
        return Prototype(self._api, **args)

    def prototype_list(self, paging=None, **args) -> PrototypeList:
        return PrototypeList(self._api, paging=paging, **args)

    def provider(self, **args) -> Provider:
        return Provider(self._api, **args)

    def provider_list(self, paging=None, **args) -> ProviderList:
        return ProviderList(self._api, paging=paging, **args)

    def provider_prototype(self, **args) -> ProviderPrototype:
        return ProviderPrototype(self._api, **args)

    def provider_prototype_list(self, paging=None, **args) -> ProviderPrototypeList:
        return ProviderPrototypeList(self._api, paging=paging, **args)

    def service(self, **args) -> Service:
        return Service(self._api, **args)

    def service_list(self, paging=None, **args) -> ServiceList:
        return ServiceList(self._api, paging=paging, **args)

    def service_prototype(self, **args) -> ServicePrototype:
        return ServicePrototype(self._api, **args)

    def service_prototype_list(self, paging=None, **args) -> ServicePrototypeList:
        return ServicePrototypeList(self._api, paging=paging, **args)

    def _upload(self, bundle_stream) -> Bundle:
        self._api.objects.stack.upload.create(file=bundle_stream)
        data = self._api.objects.stack.load.create(bundle_file="file")
        return self.bundle(bundle_id=data['id'])

    @allure_step('Upload bundle from "{1}"')
    def upload_from_fs(self, dirname) -> Bundle:
        return self._upload(stream.file(dirname))

    @allure_step('Upload bundle from "{1}"')
    def upload_from_url(self, url) -> Bundle:
        return self._upload(stream.web(url))

    @allure_step("Delete bundle")
    def bundle_delete(self, **args):
        self._api.objects.stack.bundle.delete(bundle_id=self.bundle(**args).bundle_id)
