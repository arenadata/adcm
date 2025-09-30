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

from collections import defaultdict
from pathlib import Path

from adcm.feature_flags import use_new_config_processing
from core import config
from core.types import CoreObjectDescriptor, HostGroupDescriptor
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from cm import converters
from cm.models import (
    ADCM,
    ConfigHostGroup,
    ConfigLog,
    MainObject,
    ObjectConfig,
    Prototype,
)
from cm.services.config import convert_adcm_meta_to_attr
from cm.services.config_service import prepare, retrieve


def new_config_by_descriptor(
    configuration: config.Configuration,
    description: str,
    owner: CoreObjectDescriptor | HostGroupDescriptor,
):
    match owner:
        case CoreObjectDescriptor(type=t):
            model = converters.core_type_to_model(t)
        case HostGroupDescriptor():
            model = ConfigHostGroup

    orm_owner = model.objects.only("id", "config").get(id=owner.id)

    return new_config(configuration=configuration, description=description, owner=orm_owner)


def new_config(
    configuration: config.Configuration,
    description: str,
    owner: MainObject | ConfigHostGroup | ADCM,
) -> ConfigLog:
    meta_like_attr = defaultdict(dict)
    for name, value in configuration.attributes.items():
        if value.activation:
            meta_like_attr[name]["isActive"] = value.is_active

        if value.synchronization:
            meta_like_attr[name]["isSynchronized"] = value.is_synced

    attr = convert_adcm_meta_to_attr(meta_like_attr)

    # maybe shouldn't be in here
    if not owner.config:
        owner.config = ObjectConfig.objects.create(current=0, previous=0)
        owner.save(update_fields=["config"])

    config_log = ConfigLog.objects.create(
        obj_ref=owner.config, config=configuration.values, attr=attr, description=description
    )

    owner.config.previous = owner.config.current
    owner.config.current = config_log.pk
    owner.config.save(update_fields=["previous", "current"])

    return config_log


# Use `initiate_config_if_required` after update, kept `init_object_config` for simplicity.
# Now it's still used in some places like ADCM init and upgrade for "routing" based on new config processing.
#
# signature refers to original `init_object_config`
def init_object_config(proto: Prototype, obj: MainObject) -> ObjectConfig | None:
    if use_new_config_processing():
        if not isinstance(obj, (ADCM, MainObject)):
            raise TypeError(f"Unexpected type {type(obj)}")

        # read as create.initial_config_if_requied
        return initial_config_if_required(obj, files_dir=settings.FILE_DIR)

    from cm.adcm_config.config import init_object_config as init_object_config_old

    return init_object_config_old(proto, obj)


def initial_config_if_required(owner_object: MainObject | ADCM, files_dir: Path) -> ObjectConfig | None:
    owner_descriptor = converters.orm_object_to_core_descriptor(owner_object)

    try:
        # Now it'll be encrypted, so need to make it configurable for `get_specification`
        specification, defaults = retrieve.get_specification(owner=owner_descriptor)
    except ObjectDoesNotExist:
        return None

    default_config = prepare.default_configuration(default_values=defaults, specification=specification)

    # read as create.new_config
    new_config(configuration=default_config, description="init", owner=owner_object)

    # No sense in using it in here, but for now I can't split it from init config replacement.
    # In future it'll be nice to write all files for all created configs at the end of operation
    # OR even after transaction (thou it will break "consistency" that created object has correct config)
    prepare.file_parameter_values_on_fs(
        configuration=default_config,
        specification=specification,
        owner_prefix=f"{owner_descriptor.type.value.lower()}.{owner_descriptor.id}",
        target_dir=files_dir,
    )

    # todo make separate method or update usages
    owner_object.refresh_from_db(fields=["config"])
    return owner_object.config
