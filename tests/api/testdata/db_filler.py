"""Fill DB methods"""
# pylint: disable=invalid-name

import random
from time import sleep
from collections import defaultdict

import allure

from tests.steps.common import assume_step
from tests.test_data.getters import get_endpoint_data, get_object_data
from tests.utils.api_objects import Request, ExpectedResponse, ADSSApi
from tests.utils.endpoints import Endpoints
from tests.utils.methods import Methods
from tests.utils.types import (
    get_fields,
    Field,
    is_fk_field,
    ForeignKeyM2M,
    ForeignKey,
    get_field_name_by_fk_dataclass,
)


# pylint: disable=too-few-public-methods
class DbFiller:
    """Utils to prepare data in DB before test"""

    __slots__ = ("adss", "_available_fkeys", "_used_fkeys", "_set_null_capacities")

    capacity_endpoints = (Endpoints.ClusterCapacity, Endpoints.FileSystemCapacity)

    def __init__(self, adss: ADSSApi, set_null_capacities=True):
        self.adss = adss
        self._available_fkeys = defaultdict(set)
        self._used_fkeys = {}
        self._set_null_capacities = set_null_capacities

    @allure.step("Generate valid request data")
    def generate_valid_request_data(self, endpoint: Endpoints, method: Methods) -> dict:
        """
        Return valid request body and url params for endpoint and method combination
        """
        # POST
        if method == Methods.POST:
            return {
                "data": self._get_or_create_data_for_endpoint(
                    endpoint=endpoint,
                    force=True,
                    prepare_data_only=True,
                    set_null_capacities=self._set_null_capacities,
                )[0],
                "url_params": {},
            }
        # LIST
        if method == Methods.LIST:
            self._get_or_create_multiple_data_for_endpoint(endpoint=endpoint, count=3)
            return {"data": None, "url_params": {}}

        full_item = get_object_data(
            adss=self.adss,
            endpoint=endpoint,
            object_id=self._get_or_create_data_for_endpoint(
                endpoint=endpoint, set_null_capacities=self._set_null_capacities
            )[0]['id'],
        )
        # GET, DELETE
        if method in (Methods.GET, Methods.DELETE):
            return {"data": None, "url_params": {}, "object_id": full_item["id"]}
        # PUT, PATCH
        if method in (Methods.PUT, Methods.PATCH):
            changed_fields = {}
            for field in get_fields(endpoint.data_class, predicate=lambda x: x.changeable):
                if isinstance(field.f_type, ForeignKey):
                    fk_data = self._get_or_create_data_for_endpoint(
                        endpoint=Endpoints.get_by_data_class(field.f_type.fk_link), force=True
                    )
                    if isinstance(field.f_type, ForeignKeyM2M):
                        changed_fields[field.name] = [{'id': el["id"]} for el in fk_data]
                    else:
                        changed_fields[field.name] = {"id": fk_data[0]["id"]}
                elif field.name != "id":
                    changed_fields[field.name] = self._generate_field_value(
                        field=field, old_value=full_item[field.name]
                    )
            result = {
                "full_item": full_item.copy(),
                "changed_fields": changed_fields,
                "url_params": {},
                "object_id": full_item["id"],
            }
            full_item.update(changed_fields)
            result["data"] = full_item
            return result
        raise ValueError(f"No such method {method}")

    def _get_or_create_data_for_endpoint(
        self, endpoint: Endpoints, force=False, prepare_data_only=False, set_null_capacities=False
    ):
        """
        Get data for endpoint with data preparation
        """
        # Job History should be filled using custom algorithm
        if endpoint in (Endpoints.JobHistory,):
            return self._generate_data_for_special_endpoints(endpoint=endpoint)

        for data_class in endpoint.data_class.predefined_dependencies:
            self._get_or_create_data_for_endpoint(
                endpoint=Endpoints.get_by_data_class(data_class), force=force
            )

        if force and not prepare_data_only and Methods.POST not in endpoint.methods:
            if current_ep_data := get_endpoint_data(adss=self.adss, endpoint=endpoint):
                return current_ep_data
            raise ValueError(
                f"Force data creation is not available for {endpoint.path}"
                "and there is no any existing data"
            )

        if not force:
            # try to fetch data from current endpoint
            if current_ep_data := get_endpoint_data(adss=self.adss, endpoint=endpoint):
                return current_ep_data

        data = self._prepare_data_for_object_creation(endpoint=endpoint, force=force)

        for data_class in endpoint.data_class.implicitly_depends_on:
            self._get_or_create_data_for_endpoint(
                endpoint=Endpoints.get_by_data_class(data_class), force=force
            )

        # If set_null_capacities requested we need to set null for all capacities
        # before creating Job in Job Queue
        if endpoint == Endpoints.JobQueue and set_null_capacities:
            self._set_null_values_for_capacities()

        if not prepare_data_only:
            response = self.adss.exec_request(
                request=Request(endpoint=endpoint, method=Methods.POST, data=data),
                expected_response=ExpectedResponse(
                    status_code=Methods.POST.value.default_success_code
                ),
            )
            return [response.json()]
        return [data]

    def _prepare_data_for_object_creation(self, endpoint: Endpoints, force=False):
        data = {}
        for field in get_fields(
            data_class=endpoint.data_class,
            predicate=lambda x: x.name != "id" and x.postable and is_fk_field(x),
        ):
            fk_data = get_endpoint_data(
                adss=self.adss, endpoint=Endpoints.get_by_data_class(field.f_type.fk_link)
            )
            if not fk_data or force:
                fk_data = self._get_or_create_data_for_endpoint(
                    endpoint=Endpoints.get_by_data_class(field.f_type.fk_link), force=force
                )
            data[field.name] = self._choose_fk_field_value(field=field, fk_data=fk_data)
        for field in get_fields(
            data_class=endpoint.data_class,
            predicate=lambda x: x.name != "id" and x.postable and not is_fk_field(x),
        ):
            data[field.name] = self._generate_field_value(field=field)

        return data

    def _get_or_create_multiple_data_for_endpoint(self, endpoint: Endpoints, count: int):
        """
        Method for multiple data creation for given endpoint.
        For each object new object chain will be created.
        If endpoint does not allow data creation of any kind (POST, indirect creation, etc.)
        method will proceed without data creation or errors
        IMPORTANT: Class context _available_fkeys and _used_fkeys
                   will be relevant only for the last object in set
        """
        current_ep_data = get_endpoint_data(adss=self.adss, endpoint=endpoint)
        if len(current_ep_data) < count:
            for _ in range(count - len(current_ep_data)):
                # clean up context before generating new element
                self._available_fkeys = defaultdict(set)
                self._used_fkeys = {}
                self._get_or_create_data_for_endpoint(
                    endpoint=endpoint,
                    force=True,
                    prepare_data_only=False,
                    set_null_capacities=self._set_null_capacities,
                )
                if len(get_endpoint_data(adss=self.adss, endpoint=endpoint)) > count:
                    break

    @allure.step("Set '0' values for capacities")
    def _set_null_values_for_capacities(self):
        """
        To stop Jobs execution and changing in Job Queue
        we need to set value=0 for all capacities.
        Method set value=0 for all currently existing capacities.
        """
        for endpoint in self.capacity_endpoints:
            objects = get_endpoint_data(adss=self.adss, endpoint=endpoint)
            for obj in objects:
                self.adss.exec_request(
                    request=Request(
                        endpoint=endpoint,
                        method=Methods.PATCH,
                        object_id=obj["id"],
                        data={"value": 0},
                    ),
                    expected_response=ExpectedResponse(
                        status_code=Methods.PATCH.value.default_success_code
                    ),
                )

    def _generate_data_for_special_endpoints(self, endpoint: Endpoints):
        """
        Data for some endpoints can be generated with custom logics
        This logics is implemented here
        """
        if endpoint == Endpoints.JobHistory:
            # To fill Job History we need to create item in Job Queue
            # and wait until it will be finished and added to Job History
            old_data = get_endpoint_data(adss=self.adss, endpoint=endpoint)
            self._get_or_create_data_for_endpoint(endpoint=Endpoints.JobQueue)
            timeout = 300
            interval = 0.5
            time_passed = 0
            while (
                len(data := get_endpoint_data(adss=self.adss, endpoint=endpoint)) <= len(old_data)
                and time_passed < timeout  # noqa: W503
            ):
                sleep(interval)
                time_passed += interval
            if data:
                return data
            raise TimeoutError(f"Data for {endpoint} was not created in {timeout} seconds")
        raise NotImplementedError(f"There is no special generator for {endpoint}")

    def _generate_field_value(self, field: Field, old_value=None):
        """Generate field value. If old_value is passed new value will be generated"""
        related_value = None
        if field.f_type.relates_on:
            related_value = get_object_data(
                adss=self.adss,
                endpoint=Endpoints.get_by_data_class(field.f_type.relates_on.data_class),
                object_id=self._used_fkeys[field.f_type.relates_on.data_class.__name__],
            )[field.f_type.relates_on.field.name]
        if old_value is not None:
            return field.f_type.generate_new(old_value=old_value, schema=related_value)
        return field.f_type.generate(schema=related_value)

    def _choose_fk_field_value(self, field: Field, fk_data: list):
        """Choose a random fk value for the specified field"""
        if isinstance(field.f_type, ForeignKey):
            fk_class_name = field.f_type.fk_link.__name__
            if fk_class_name in self._available_fkeys:
                new_fk = False
                fk_vals = self._available_fkeys[fk_class_name]
            else:
                new_fk = True
                fk_vals = {el["id"] for el in fk_data}

            if isinstance(field.f_type, ForeignKeyM2M):
                keys = random.sample(fk_vals, random.randint(1, len(fk_vals)))
                result = [{'id': el} for el in keys]
                # we do not save values for M2M Fk to used keys due to the fact
                # that we have no idea how to properly use it
                self._available_fkeys[fk_class_name].update(keys)
                if new_fk:
                    self._add_child_fk_values_to_available_fkeys(
                        fk_ids=keys, fk_data_class=field.f_type.fk_link
                    )
            else:
                key = random.choice(list(fk_vals))
                result = {'id': key}
                self._used_fkeys[fk_class_name] = key
                self._available_fkeys[fk_class_name].add(key)
                if new_fk:
                    self._add_child_fk_values_to_available_fkeys(
                        fk_ids=[key], fk_data_class=field.f_type.fk_link
                    )
            return result
        # if field is not FK
        raise ValueError("Argument field is not FKey!")

    def _add_child_fk_values_to_available_fkeys(self, fk_ids: list, fk_data_class):
        """Add information about child FK values to metadata for further consistency"""
        for child_fk_field in get_fields(data_class=fk_data_class, predicate=is_fk_field):
            fk_field_name = get_field_name_by_fk_dataclass(
                data_class=fk_data_class, fk_data_class=child_fk_field.f_type.fk_link
            )
            for fk_id in fk_ids:
                fk_data = get_object_data(
                    adss=self.adss,
                    endpoint=Endpoints.get_by_data_class(fk_data_class),
                    object_id=fk_id,
                )
                if isinstance(child_fk_field.f_type, ForeignKeyM2M):
                    self._available_fkeys[child_fk_field.f_type.fk_link.__name__].update(
                        [el["id"] for el in fk_data[fk_field_name]]
                    )
                elif isinstance(child_fk_field.f_type, ForeignKey):
                    self._available_fkeys[child_fk_field.f_type.fk_link.__name__].add(
                        fk_data[fk_field_name]["id"]
                    )

    @allure.step("Generate new value for unchangeable FK_field")
    def generate_new_value_for_unchangeable_fk_field(self, f_type, current_field_value):
        """Generate new value for unchangeable fk fields"""
        if not isinstance(f_type, ForeignKey):
            raise ValueError("Field type is not ForeignKey")
        new_objects = get_endpoint_data(self.adss, Endpoints.get_by_data_class(f_type.fk_link))
        if len(new_objects) == 1:
            with assume_step(
                f'Data creation is not available for {f_type.fk_link}', exception=ValueError
            ):
                new_objects = self._get_or_create_data_for_endpoint(
                    endpoint=Endpoints.get_by_data_class(f_type.fk_link), force=True
                )
        valid_new_objects = [obj for obj in new_objects if obj["id"] != current_field_value["id"]]
        if valid_new_objects:
            return {"id": valid_new_objects[0]["id"]}
        with allure.step("Failed to create new data. Returning a non-existent object"):
            return {"id": 42}
