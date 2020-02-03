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
import { getControlType, getPattern } from '@app/core/types';

import { FieldOptions, PanelOptions, ConfigValueTypes } from './types';

export type simpleType = 'string' | 'integer' | 'float' | 'bool' | 'int' | 'one_of' | 'dict_key_selection';
export type reqursionType = 'list' | 'dict';
export type matchType = simpleType | reqursionType;

interface Iroot {
  match: matchType;
  selector?: string;
  variants?: { [key: string]: string };
  item?: string;
  items?: { [key: string]: string };
  required_items?: string[];
  default_item?: string;
}

export interface IYspec {
  [key: string]: Iroot;
}

class Field {
  private _options: Partial<FieldOptions>;
  constructor(public key: string, private value: simpleType) {
    this._options = {
      display_name: this.key,
      name: this.key,
      key: this.key,
      subname: null,
      controlType: getControlType(this.value),
      type: this.value as ConfigValueTypes,
      validator: {
        required: true,
        pattern: getPattern(this.value)
      },
      hidden: false,
      read_only: false,
      compare: []
    };
  }
  get options() {
    return this._options;
  }
  setSubname(name: string) {
    this._options.subname = name;
    return this;
  }
  setKey(key: string) {
    this._options.key = `${this.key}/${key}`;
    return this;
  }
  setValue(value: simpleType) {
    this._options.default = value;
    this._options.value = value;
    return this;
  }
}

class Group {
  constructor(public key: string, private value: reqursionType) {}
  options(value: simpleType) {
    return {};
  }
  setSubname(name: string) {
    //this._options.subname = name;
    return this;
  }
  setValue(value: simpleType) {
    // this.options.default = value;
    // this.options.value = value;
    return this;
  }
  setKey(key: string) {
    return this;
  }
}

export class YspecStructure {
  yspec: IYspec;
  source: FieldOptions;
  output: PanelOptions;

  constructor(options: FieldOptions) {
    this.source = options;
    this.yspec = options.limits.yspec;
    this.output = this[this.yspec.root.match](options);
  }

  getModel(rules: { [key: string]: string }) {
    return Object.keys(rules).map(key => {
      const value = rules[key];
      if (value as simpleType) return new Field(key, <simpleType>value);
      else return new Group(key, <reqursionType>value);
    });
  }

  list(source: FieldOptions) {
    const scheme = { ...source.limits.yspec };

    const value = Array.isArray(source.value) ? source.value : Array.isArray(source.default) ? source.default : null;

    const item = scheme.root.item;
    const rule = scheme[item];

    if (rule.match === 'dict') {
      const model = this.getModel(rule.items);
      /**
       * fill the model to data (value or default)
       */
      return {
        ...source,
        type: 'group',
        options: value.map((v, i) => {
          if (typeof v === 'object') {
            return {
              display_name: `--- ${i} ---`,
              name: i.toString(),
              key: `${i}/${source.key}`,
              type: 'group',
              options: Object.keys(v).map(
                k =>
                  model
                    .find(m => m.key === k)
                    .setKey(`${i}/${source.key}`)
                    .setValue(v[k]).options
              )
            };
          }
        })
      };
    }
  }

  dict(source: FieldOptions) {
    return {
      ...source,
      type: 'group',
      options: this.getFields(source)
    };
  }

  getFields(source: FieldOptions, selector = 'root') {
    let scheme = { ...source.limits.yspec };

    const root = scheme[selector],
      value = typeof source.value === 'object' ? source.value : typeof source.default === 'object' ? source.default : null;

    const items = root.items;
    if (items) {
      return Object.keys(items).map(k => {
        const rule = scheme[items[k]];
        if (rule.match !== 'dict') {
          return {
            display_name: k,
            name: k,
            key: `${k}/${source.key}`,
            subname: null,
            default: source.default[k],
            value: value[k],
            hidden: false,
            read_only: false,
            controlType: getControlType(rule.match),
            type: rule.match,
            validator: {
              required: !!(root.required_items && root.required_items.includes[k]),
              pattern: getPattern(rule.match)
            },
            compare: []
          };
        } else {
          scheme.root = rule;
          const key = `${k}/${source.key}`;
          source.key = key;
          source.value = value[k];
          source.default = source.default[k];
          return {
            display_name: k,
            name: k,
            key,
            default: source.default[k],
            value: value[k],
            hidden: false,
            read_only: false,
            type: 'group',
            options: this.getFields(source, items[k]),
            limits: {
              yspec: scheme
            }
          };
        }
      });
    } else {
      console.warn('Yspec :: Items not found');
      return [];
    }
  }
}
