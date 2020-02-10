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
import { getControlType, getPattern, IRoot } from '@app/core/types';

import { controlType } from '../field.service';

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

export interface IField {
  name: string;
  type: simpleType;
  path: string[];
  controlType: controlType;
  validator: {
    required: boolean;
    pattern: RegExp | null;
  };
}

export class YspecService {
  private root: IYspec;
  private output: any;

  constructor() {}

  set Root(yspec: IYspec) {
    this.root = yspec;
  }

  get Root() {
    return this.root;
  }

  build(rule = 'root', path: string[] = []) {
    const { match, item, items } = { ...this.Root[rule] };

    switch (match) {
      case 'list':
        return this.list(item, path);
      case 'dict':
        return this.dict(items, path);
      // case 'one_of':
      //   return this.one_of();
      // case 'dict_key_selection':
      //   return this.dict_key_selection();
      default:
        return this.field({ type: match, path });
    }
  }

  field(field: { path: string[]; type: simpleType }): IField {
    const [name, ...o] = [...field.path].reverse();
    return {
      name,
      type: field.type,
      path: field.path,
      controlType: getControlType(field.type),
      validator: {
        required: this.findRule(field.path, 'required_items'),
        pattern: getPattern(field.type)
      }
    };
  }

  findRule(path: string[], name: string): boolean {
    const [field, ...other] = [...path].reverse();
    const rule = this.Root[other[0]];
    return !!(rule && rule[name] && rule[name][field]);
  }

  list(item: string, path: string[]): { [x: string]: any; type: string } {
    if (!this.Root[item]) throw new Error('Not itmem for list');
    const name = [...path].reverse()[0] || 'root';
    return { type: 'list', [name]: this.build(item, [...path, item]) };
  }

  dict(items: IRoot, path: string[]): { [x: string]: any; type: string } {
    const name = [...path].reverse()[0] || 'root';
    return {
      type: 'dict',
      [name]: Object.keys(items).map((item_name: string) => {
        return this.build(items[item_name], [...path, item_name]);
      })
    };
  }

  one_of() {}

  dict_key_selection() {}
}
