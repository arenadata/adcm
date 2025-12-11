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


from cm.legacy.services.config._base import (
    ConfigAttrPair,
    convert_adcm_meta_to_attr,
    convert_attr_to_adcm_meta,
    represent_json_type_as_string,
    represent_string_as_json_type,
    retrieve_config_attr_pairs,
    retrieve_configs_with_revision,
    retrieve_primary_configs,
)

__all__ = [
    "ConfigAttrPair",
    "retrieve_config_attr_pairs",
    "retrieve_primary_configs",
    "retrieve_configs_with_revision",
    "convert_attr_to_adcm_meta",
    "convert_adcm_meta_to_attr",
    "represent_json_type_as_string",
    "represent_string_as_json_type",
]
