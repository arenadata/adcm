// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { FieldOptions, ConfigOptions, PanelOptions } from './types';
import { controlType, getPattern } from '@app/core/types';

type matchType = 'string' | 'int' | 'float' | 'bool' | 'list' | 'dict';

interface Iroot {
  match: matchType;
  selector?: string;
  variants?: { [key: string]: string };
  item?: string | matchType;
  items?: { [key: string]: string };
  required_items?: string[];
  default_item?: string;
}

interface IYspec {
  [key: string]: Iroot;
}

export class YspecStructure {
  yspec: IYspec;
  source: FieldOptions;
  output: PanelOptions;

  constructor(options: FieldOptions) {
    this.source = options;
    this.yspec = options.limits.yspec;
    this.output = this[this.yspec.root.match]();
  }

  dict() {
    return {
      ...this.source,
      type: 'group',
      options: this.getFields()
    };
  }

  getFields() {
    const scheme = this.yspec,
      root = scheme.root,
      value = typeof this.source.value === 'object' ? this.source.value : typeof this.source.default === 'object' ? this.source.default : null;

    const items = this.yspec.root.items;
    if (items) {
      return Object.keys(items).map(k => {
        const rule = scheme[items[k]];
        if (rule.match !== 'dict') {
          return {
            display_name: k,
            name: k,
            key: `${k}/${this.source.key}`,
            subname: null,
            default: this.source.default[k],
            value: value[k],
            hidden: false,
            read_only: false,
            controlType: controlType(rule.match),
            type: rule.match,
            validator: {
              required: !!(root.required_items && root.required_items.includes[k]),
              pattern: getPattern(rule.match)
            }
          };
        } else {
          return {
            display_name: k,
            name: k,
            subname: null,
            key: k,
            default: this.source.default[k],
            value: value[k],
            hidden: false,
            read_only: false,
            controlType: controlType(rule.match),
            type: rule.match,
            validator: {}
          };
        }
      });
    }
  }
}
