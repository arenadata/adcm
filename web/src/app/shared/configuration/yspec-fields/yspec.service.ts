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
import { FormGroup } from '@angular/forms';
import { controlType, getPattern } from '@app/core/types';

import { FieldOptions, FieldStack } from '../types';

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

export interface IYspec {
  [key: string]: Iroot;
}

export class YspecService {
  prepare(field: FieldOptions): FieldOptions[] {
    const scheme = field.limits.yspec,
      value: { [key: string]: string } = field.default as {};

    const root = scheme.root;
    if (root) {
      switch (root.match) {
        case 'list':
          const item = root.item;
          if (item) {
            const rule = scheme[item];

            const selector = rule.selector;

            const variants = rule.variants;

            return [
              {
                ...field,
                hidden: false,
                read_only: false,
                controlType: controlType(rule.match),
                type: rule.match,
                validator: {
                  required: !!(root.required_items && root.required_items.includes[field.name]),
                  pattern: getPattern(rule.match)
                }
              }
            ];
          }
          break;
        case 'dict':
          const items = root.items;
          if (items) {
            return Object.keys(items)
              .filter(k => scheme[items[k]].match !== 'dict')
              .map(k => {
                const rule = scheme[items[k]];
                return {
                  label: k,
                  name: k,
                  key: k,
                  subname: null,
                  default: null,
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
              });
          }
          break;
      }
    }
  }

  checkValue(data: FieldStack[], form: FormGroup) {
    data.map(field => this.checkField(field.limits.yspec, form.controls[`${field.subname ? field.subname + '/' : ''}${field.name}`] as FormGroup));
  }

  checkField(yspec: IYspec, form: FormGroup) {
    const value = form.value;
    const checked = Object.keys(value).reduce((output, key) => {
      let checkValue = value[key];
      if (yspec.root.match === 'dict') {
        /** */
        const rule = yspec[yspec.root.items[key]];
        /** */
        if (rule.match !== 'dict' && rule.match !== 'string') {
          if (rule.match === 'list') checkValue = (checkValue as string[]).map(a => this.checkSimple(a, rule.item as matchType));

          checkValue = this.checkSimple(checkValue, rule.match);
        }
      }
      output[key] = checkValue;
      return output;
    }, {});

    form.setValue(checked);
  }

  checkSimple(value: string, match: matchType) {
    if (typeof value === 'string')
      switch (match) {
        case 'int':
          return parseInt(value, 10);
        case 'float':
          return parseFloat(value);
      }

    return value;
  }
}
