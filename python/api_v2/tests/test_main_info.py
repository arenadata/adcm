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

from typing import Any

from cm.models import Component, ConfigLog
from tests.suites import ADCMDjangoAPISuite
from unittest_parametrize import param, parametrize

MAIN_INFO = "__main_info"
CONFIGS = "configs"
CONFIG_SCHEMA = "config-schema"

WITHOUT_MAIN_INFO = "without_main_info"

# each case is a component of `main_info_service` with its own `__main_info` definition:
# component name, default value of `__main_info`, is it required, status of config save with unchanged value
parametrize_cases = parametrize(
    ("name", "default", "is_required", "unchanged_save_status"),
    [
        param("required_with_default", "required with default", True, 201, id="required_with_default"),
        param("required_no_default", None, True, 409, id="required_no_default"),
        param("non_required_with_default", "non required with default", False, 201, id="non_required_with_default"),
        param("non_required_no_default", None, False, 201, id="non_required_no_default"),
        param("non_required_invisible", "non required invisible", False, 201, id="non_required_invisible"),
        param("only_main_info", "only main info", False, 201, id="only_main_info"),
    ],
)


class TestMainInfo(ADCMDjangoAPISuite):
    """
    `__main_info` is a special config parameter placed in config root of an object.
    This suite is aiming to confirm how end user interactions with API works, excluding upgrade/plugin scenarios.
    """

    maxDiff = None

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.bundle = cls.uc.upload_bundle(src=cls.test_bundles_dir / "main_info")
        cls.cluster = cls.uc.add_cluster(bundle=cls.bundle, name="main_info_cluster")
        cls.service, *_ = cls.uc.add_services_to_cluster(names=["main_info_service"], cluster=cls.cluster)

    def get_component(self, name: str) -> Component:
        return Component.objects.get(service=self.service, prototype__name=name)

    def get_current_config_log(self, component: Component) -> ConfigLog:
        component.config.refresh_from_db()

        return ConfigLog.objects.get(id=component.config.current)

    def retrieve_config(self, component: Component) -> dict[str, Any]:
        response = self.client.v2[component, CONFIGS, self.get_current_config_log(component)].get()
        self.assertEqual(response.status_code, 200)

        return response.json()["config"]

    def save_config(
        self, component: Component, config: dict[str, Any], *, expected_status: int = 201
    ) -> dict[str, Any]:
        response = self.client.v2[component, CONFIGS].post(data={"config": config, "adcmMeta": {}})
        self.assertEqual(response.status_code, expected_status, response.json())

        return response.json()

    def retrieve_main_info_of_object(self, component: Component) -> str | None:
        response = self.client.v2[component].get()
        self.assertEqual(response.status_code, 200)

        return response.json()["mainInfo"]

    def retrieve_main_info_from_components_list(self, name: str) -> str | None:
        response = self.client.v2[self.service, "components"].get()
        self.assertEqual(response.status_code, 200)

        return {entry["name"]: entry["mainInfo"] for entry in response.json()["results"]}[name]

    def get_adcm_meta(self, parameter_schema: dict[str, Any]) -> dict[str, Any]:
        # non-required parameters are wrapped in `oneOf` with `null`
        if "adcmMeta" in parameter_schema:
            return parameter_schema["adcmMeta"]

        return parameter_schema["oneOf"][0]["adcmMeta"]

    @parametrize_cases
    def test_main_info_in_config_and_on_object(
        self,
        name: str,
        default: str | None,
        is_required: bool,  # noqa: ARG002
        unchanged_save_status: int,
    ) -> None:
        component = self.get_component(name)

        # initial (default) config
        self.assertIn(MAIN_INFO, self.retrieve_config(component))
        self.assertEqual(self.retrieve_config(component)[MAIN_INFO], default)
        self.assertEqual(self.get_current_config_log(component).config[MAIN_INFO], default)
        self.assertEqual(self.retrieve_main_info_of_object(component), default)
        self.assertEqual(self.retrieve_main_info_from_components_list(name), default)

        # config saved with unchanged `__main_info`
        self.save_config(component, config=self.retrieve_config(component), expected_status=unchanged_save_status)

        self.assertEqual(self.retrieve_config(component)[MAIN_INFO], default)
        self.assertEqual(self.get_current_config_log(component).config[MAIN_INFO], default)
        self.assertEqual(self.retrieve_main_info_of_object(component), default)

        # config saved with changed `__main_info`
        changed = f"changed {name}"
        response_config = self.save_config(component, config=self.retrieve_config(component) | {MAIN_INFO: changed})

        self.assertEqual(response_config["config"][MAIN_INFO], changed)
        self.assertEqual(self.retrieve_config(component)[MAIN_INFO], changed)
        self.assertEqual(self.get_current_config_log(component).config[MAIN_INFO], changed)
        self.assertEqual(self.retrieve_main_info_of_object(component), changed)
        self.assertEqual(self.retrieve_main_info_from_components_list(name), changed)

    @parametrize_cases
    def test_main_info_in_config_schema(
        self,
        name: str,
        default: str | None,
        is_required: bool,
        unchanged_save_status: int,  # noqa: ARG002
    ) -> None:
        component = self.get_component(name)

        response = self.client.v2[component, CONFIG_SCHEMA].get()
        self.assertEqual(response.status_code, 200)

        schema = response.json()
        parameter_schema = schema["properties"].get(MAIN_INFO)

        # presence and default
        self.assertIsNotNone(parameter_schema)
        self.assertEqual(parameter_schema.get("default"), default)

        # `__main_info` is invisible regardless of `ui_options` in bundle
        self.assertTrue(self.get_adcm_meta(parameter_schema)["isInvisible"])

        # all parameters are listed in `required`, non-required ones are the ones allowed to be `null`
        self.assertIn(MAIN_INFO, schema["required"])
        self.assertEqual("oneOf" in parameter_schema, not is_required)

    @parametrize_cases
    def test_save_config_without_main_info_fail(
        self,
        name: str,
        default: str | None,  # noqa: ARG002
        is_required: bool,  # noqa: ARG002
        unchanged_save_status: int,  # noqa: ARG002
    ) -> None:
        component = self.get_component(name)
        config = {key: value for key, value in self.retrieve_config(component).items() if key != MAIN_INFO}

        response = self.client.v2[component, CONFIGS].post(data={"config": config, "adcmMeta": {}})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "CONFIG_OPERATION_ERROR")
        self.assertIn(MAIN_INFO, response.json()["desc"])

    def test_component_without_main_info(self) -> None:
        component = self.get_component(WITHOUT_MAIN_INFO)

        # config
        self.assertNotIn(MAIN_INFO, self.retrieve_config(component))
        self.assertNotIn(MAIN_INFO, self.get_current_config_log(component).config)

        # config schema
        response = self.client.v2[component, CONFIG_SCHEMA].get()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(MAIN_INFO, response.json()["properties"])

        # object's own endpoint
        self.assertIsNone(self.retrieve_main_info_of_object(component))
        self.assertIsNone(self.retrieve_main_info_from_components_list(WITHOUT_MAIN_INFO))
