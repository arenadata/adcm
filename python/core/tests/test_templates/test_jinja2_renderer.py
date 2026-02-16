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

from pathlib import Path
from unittest import TestCase

from core.templates._renderers import TemplateRendererJinja2
from core.templates._types import RendererEnv, TemplateFile


class TestBugs(TestCase):
    def test_adcm_7403(self):
        template = Path(__file__).parent / "files" / "bugs" / "ADCM-7403.j2"
        renderer = TemplateRendererJinja2(
            args=TemplateFile(path=template), env=RendererEnv(discovery_root=template.parent)
        )

        result = renderer.render({"value": ["10.12.40.30"]})

        self.assertEqual(result, [{"default": ["10.12.40.30"]}])


class TestJinja2Renderer(TestCase):
    def setUp(self):
        self.context = {"value": "test ' test"}

    def test_render_jinja2(self):
        template = Path(__file__).parent / "files" / "jinja2" / "ADCM-7423.j2"
        renderer = TemplateRendererJinja2(
            args=TemplateFile(path=template), env=RendererEnv(discovery_root=template.parent)
        )

        result = renderer.render(self.context)

        self.assertEqual(result, [{"name": "test ' test"}])

    def test_render_html(self):
        template = Path(__file__).parent / "files" / "html" / "ADCM-7423.html"
        renderer = TemplateRendererJinja2(
            args=TemplateFile(path=template), env=RendererEnv(discovery_root=template.parent)
        )

        result = renderer.render(self.context)

        self.assertEqual(result, "<h1>test &#39; test</h1>")

    def test_render_yaml(self):
        template = Path(__file__).parent / "files" / "yaml" / "ADCM-7423.yaml"
        renderer = TemplateRendererJinja2(
            args=TemplateFile(path=template), env=RendererEnv(discovery_root=template.parent)
        )

        result = renderer.render(self.context)

        self.assertEqual(result, [{"name": "test ' test"}])
