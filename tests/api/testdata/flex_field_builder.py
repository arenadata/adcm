"""FlexFieldBuilder implementation"""
# pylint: disable=no-else-return
import random
from copy import deepcopy
from typing import List, Union

from tests.test_data.getters import get_object_data
from tests.utils.api_objects import ADSSApi
from tests.utils.endpoints import Endpoints
from tests.utils.methods import Methods
from tests.utils.tools import nested_set
from tests.utils.types import Field, is_huge_field, is_fk_or_back_ref, get_fields


class FlexFieldBuilder:
    """
    Builder can help to build expected body for flex field checks
    """

    def __init__(self, adss: ADSSApi, method: Methods):
        self.adss = adss
        self.method = method

    def expand_fk_by_chain_if_possible(
        self, endpoint: Endpoints, body: dict, fields_chain: list
    ) -> bool:
        """
        Expand fk for all fk values by chain, e.g ['cluster', 'type']
        Expands only last chain level.
        """
        first_field, next_fields = fields_chain[0], fields_chain[1:]
        fk_endpoint = endpoint.get_child_endpoint_by_fk_name(first_field)
        if not next_fields:
            return self._expand_fk_by_field_if_possible(
                endpoint, fk_endpoint, body=body, field_name=first_field
            )
        if isinstance(body, dict):
            return self.expand_fk_by_chain_if_possible(
                fk_endpoint, body=body.get(first_field), fields_chain=next_fields
            )
        elif isinstance(body, list):
            results = []
            for value in body:
                results.append(
                    self.expand_fk_by_chain_if_possible(
                        fk_endpoint, body=value.get(first_field), fields_chain=next_fields
                    )
                )
            return any(results)
        else:
            return False

    def _expand_fk_by_field_if_possible(
        self,
        parent_endpoint: Endpoints,
        fk_endpoint: Endpoints,
        body: [dict, list],
        field_name: str,
    ) -> bool:
        """
        Expand fk value by field
        If fk field value is list, it's m2m value, and full value would be set for each m2m object
        If fk field value is dict - it's simple fk value, and full body will just be set
        If fk field value is empty, field can't be expanded and return False
        Return True if field can be expanded
        """
        is_m2m_field_values = isinstance(body, list)
        is_fk_field_values = isinstance(body, dict)
        can_be_expanded = False
        if is_m2m_field_values:
            for index, current_body in enumerate(body):
                full_body = get_object_data(
                    self.adss, parent_endpoint, object_id=current_body.get('id')
                )
                if full_body.get(field_name):
                    can_be_expanded = True
                    fk_object_data = self._get_expanded_data_for_fk(
                        fk_endpoint, full_body.get(field_name)
                    )
                    chain = [index, field_name]
                    nested_set(body, keys=chain, value=fk_object_data)
        elif is_fk_field_values:
            full_body = get_object_data(self.adss, parent_endpoint, object_id=body.get('id'))
            if full_body.get(field_name):
                fk_object_data = self._get_expanded_data_for_fk(
                    fk_endpoint, full_body.get(field_name)
                )
                body[field_name] = fk_object_data
                can_be_expanded = True
        return can_be_expanded

    @staticmethod
    def limit_fields(data: Union[dict, list], fields: List[Field]):
        """
        Return data only with fields
        """
        if isinstance(data, list):
            expand_field_value = []
            for field_value in data:
                expand_field_value.append({field.name: field_value[field.name] for field in fields})
        else:
            expand_field_value = {field.name: data[field.name] for field in fields}
        return expand_field_value

    @staticmethod
    def omit_fields(data: Union[dict, list], fields: List[Field]):
        """
        Return data without fields
        """
        data = deepcopy(data)
        if isinstance(data, list):
            for field_value in data:
                for field in fields:
                    field_value.pop(field.name)
        else:
            for field in fields:
                data.pop(field.name)
        return data

    def choose_not_empty_field(self, endpoint: Endpoints, data: Union[dict, list],
                               fields: List[Field]):
        """
        Return random field with not-empty value in full object data
        Full object data taken by data['id'] attribute
        """
        fields = deepcopy(fields)
        if isinstance(data, dict):
            full_body = get_object_data(self.adss, endpoint, object_id=data.get('id'))
            while not full_body[(not_empty_field := random.choice(fields)).name]:
                fields.remove(not_empty_field)
            return not_empty_field
        elif isinstance(data, list):
            full_bodies = [
                get_object_data(self.adss, endpoint, object_id=value.get('id')) for value in data
            ]
            for not_empty_field in fields:
                all_values = [body[not_empty_field.name] for body in full_bodies]
                if any(all_values):
                    return not_empty_field
        return None

    def _get_expanded_data_for_fk(self, endpoint, fk_value):
        """
        Get body for expanded fk field without huge fields
        fk_value - not-expanded value from response
        """
        if isinstance(fk_value, list):
            body = []
            for value in fk_value:
                object_id = value.get('id')
                one_field_body = get_object_data(self.adss, endpoint=endpoint, object_id=object_id)
                if self.method == Methods.LIST:
                    one_field_body = self._prepare_body_for_list(endpoint, one_field_body)
                body.append(one_field_body)
        elif fk_value is None:
            body = None
        else:
            object_id = fk_value.get('id')
            body = (
                get_object_data(self.adss, endpoint=endpoint, object_id=object_id)
                if object_id
                else {}
            )
            if self.method == Methods.LIST:
                body = self._prepare_body_for_list(endpoint, body)
        return body

    def _prepare_body_for_list(self, endpoint: Endpoints, body: dict):
        """
        LIST response is different from READ
         - LIST response doesn't contain huge and fk fields
         - LIST response contain link to full object in 'url' attribute
        """
        body = self._drop_data_fields_by_predicate(
            endpoint=endpoint, data=body, predicate=is_huge_field
        )
        body = self._drop_data_fields_by_predicate(
            endpoint=endpoint, data=body, predicate=is_fk_or_back_ref
        )
        body['url'] = self.adss.get_url_for_endpoint(
            endpoint, Methods.GET, object_id=body.get('id')
        )
        return body

    @staticmethod
    def _drop_data_fields_by_predicate(endpoint: Endpoints, data: dict, predicate):
        """
        Drop data fields for endpoint by predicate
        """
        fields = list(
            field.name for field in get_fields(endpoint.data_class, predicate=predicate)
        )
        return {key: value for key, value in data.items() if key not in fields}
