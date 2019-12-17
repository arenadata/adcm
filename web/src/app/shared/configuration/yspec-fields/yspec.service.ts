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
      value = typeof field.value === 'object' ? field.value : typeof field.default === 'object' ? field.default : null;

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
            return Object.keys(items).map(k => {
              const rule = scheme[items[k]];

              if (rule.match !== 'dict') {
                return {
                  display_name: k,
                  name: k,
                  key: k,
                  subname: null,
                  default: field.default,
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
                scheme.root = rule;
                return {
                  display_name: k,
                  name: k,
                  subname: null,
                  key: k,
                  limits: {
                    yspec: scheme
                  },
                  default: field.default,
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
          break;
      }
    }
  }

  checkValue(data: FieldStack[], form: FormGroup): { [key: string]: any } {
    return data.reduce((output, field) => {
      const key = `${field.subname ? field.subname + '/' : ''}${field.name}`;
      output[key] = this.checkField(field.limits.yspec, form.controls[key] as FormGroup);
      return output;
    }, {});
  }

  checkField(yspec: IYspec, form: FormGroup): { [key: string]: any } {
    const value = form.value;
    return Object.keys(value).reduce((output, key) => {
      let checkValue = value[key];
      if (yspec.root.match === 'dict') {
        /** */
        const rule = yspec[yspec.root.items[key]] || yspec[key];
        /** */
        if (rule.match !== 'dict' && rule.match !== 'string') {
          if (rule.match === 'list') {
            /** TODO
             *  !!!!!!!!! checkValue never empty
             */
            checkValue = checkValue && (checkValue as string[]).map(a => this.checkSimple(a, rule.item as matchType));
          }

          checkValue = this.checkSimple(checkValue, rule.match);
        } else if (rule.match === 'dict') {
          /** recursion this */

          const fg = form.controls[key] as FormGroup;
          checkValue = this.checkField(yspec, fg);

          //debugger;
        }
      }
      output[key] = checkValue;
      return output;
    }, {});
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
