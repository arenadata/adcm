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
import { FieldOptions } from '../types';
import { getPattern, controlType } from '@app/core/types';

const SimpleMatch = ['string', 'int', 'float', 'bool', 'list'];

type matchType = 'string' | 'int' | 'float' | 'bool' | 'list' | 'dict';

interface Iroot {
  match: matchType;
  selector?: string;
  variants?: { [key: string]: string };
  item?: string;
  items?: { [key: string]: string };
  required_items?: string[];
  default_item?: string;
}

export class YspecService {
  prepare(scheme: { [key: string]: Iroot }, value: { [key: string]: string }): FieldOptions[] {
    const root = scheme.root;
    if (root) {
      switch (root.match) {
        case 'list':
          break;
        case 'dict':
          const items = root.items;
          if (items) {
            return Object.keys(items)
              .filter(k => SimpleMatch.includes(scheme[items[k]].match))
              .map(k => {
                const rule = scheme[items[k]];
                return {
                  label: k,
                  name: k,
                  hidden: false,
                  read_only: false,
                  key: k,
                  subname: '',
                  default: null,
                  value: value[k],
                  controlType: controlType(rule.match),
                  type: rule.match,
                  validator: { pattern: getPattern(rule.match) },
                  required: (root.required_items && root.required_items.includes[k]) || false
                };
              });
          }
          break;
      }
    }
  }
}
