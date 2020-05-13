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
import { controlType } from '@app/shared/configuration/types';
import { matchType } from '@app/shared/configuration/yspec/yspec.service';

import { InnerIssue, Issue } from './issue';

export function getPattern(name: string): RegExp {
  const fn = {
    integer: () => new RegExp(/^[-]?\d+$/),
    int: () => new RegExp(/^[-]?\d+$/),
    float: () => new RegExp(/^[-]?[0-9]+(\.[0-9]+)?$/)
  };
  return fn[name] ? fn[name]() : null;
}

export function getControlType(name: string): controlType {
  const a: Partial<{[key in matchType | controlType]: controlType}> = {
    bool: 'boolean',
    int: 'textbox',
    integer: 'textbox',
    float: 'textbox',
    string: 'textbox',
    file: 'textarea',
    text: 'textarea'
  };
  return a[name] || name;
}

export function isBoolean(value) {
  return typeof value === 'boolean';
}

export function isObject(value) {
  return value !== null && typeof value === 'object';
}

export function isNumber(value) {
  return typeof value === 'number' && !isNaN(value);
}

const IssueName = {
  config: 'configuration',
  host_component: 'host - components'
};
export function issueMessage(e: { id: number; name: string; issue: Issue }, typeName: string) {
  if (e.issue)
    return Object.keys(e.issue).reduce((a, c) => {
      if (typeof e.issue[c] === 'object') {
        const inner = e.issue[c] as InnerIssue;
        return `${a}<div>${c}: <b>${inner.name}</b>${issueMessage(inner, c)}</div>`;
      } else return `<li><a href="/${typeName}/${e.id}/${c}">${IssueName[c]}</a></li>`;
    }, '');
}

/**
 * Remove empty, null, undefined properties
 */
export function clearEmptyField(input: Object): Object {
  return Object.keys(input).reduce((output, key) => {
    const value = input[key];

    if (isObject(value) && !Array.isArray(value) && Object.keys(input[key]).length) {
      const result = clearEmptyField(value);
      if (Object.keys(result).length) output[key] = result;
    } else if (isBoolean(value) || isNumber(value) || value) output[key] = value;

    return output;
  }, {});
}

/**
 * Support nullable value in object properties,
 * if value input field is empty return null.
 */
export function nullEmptyField(input: Object): Object {
  return Object.keys(input).reduce((output, key) => {
    const data = input[key];
    if (isObject(data) && !Array.isArray(data)) {
      output[key] = nullEmptyField(data);
      if (!Object.keys(output[key]).length) delete output[key];
    } else if ((typeof data === 'number' && isNaN(data)) || (typeof data === 'string' && !data) || data === null) output[key] = null;
    else if (isBoolean(data) || (typeof data === 'number' && data === 0) || data) output[key] = data;
    return output;
  }, {});
}

/**
 * Utility function for a array,
 * flattening an array of arrays
 * @param a
 */
export function flatten<T>(a: T[]) {
  return a.reduce<T[]>((acc, val) => (Array.isArray(val) ? acc.concat(flatten<T>(val)) : acc.concat(val)), []);
}

/**
 * return 16-bit hex string
 * @example '#cccccc'
 */
export function getRandomColor(): string {
  const letters = '0123456789ABCDEF';
  let color = '#';
  for (let i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)];
  }
  return color;
}

export function uniqid(prefix: string = '', isFloat: boolean = false) {
  const seed = function(s: number, w: number): string {
    const _s = s.toString(16);
    return w < _s.length ? _s.slice(_s.length - w) : w > _s.length ? new Array(1 + (w - _s.length)).join('0') + _s : _s;
  };

  let result = prefix + seed(parseInt((new Date().getTime() / 1000).toString(), 10), 8) + seed(Math.floor(Math.random() * 0x75bcd15) + 1, 5);

  if (isFloat) result += (Math.random() * 10).toFixed(8).toString();

  return result;
}

export function randomInteger(max: number, min: number = 0): number {
  return Math.floor(min + Math.random() * (max + 1 - min));
}
