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
import { InnerIssue, Issue } from './issue';

export function getPattern(name: string): RegExp {
  const fn = {
    integer: () => new RegExp(/^\d+$/),
    int: () => new RegExp(/^\d+$/),
    float: () => new RegExp(/^[0-9]+(\.[0-9]+)?$/)
  };
  return fn[name] ? fn[name]() : null;
}

export function controlType(name: string): string {
  const ControlsTypes = {
    bool: 'boolean',
    file: 'textarea',
    text: 'textarea',
    integer: 'textbox',
    float: 'textbox',
    string: 'textbox'
  };
  return ControlsTypes[name] || name;
}

export function getTypeName(name: string) {
  return name ? name.split('2')[0] : name;
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

/**
 *
 *
 * @export
 * @param {any[]} input - Input data
 * @param {*} value - Form value
 * @returns collection with inner properties
 */
export function parseValueConfig(input: any[], value: any) {
  return input.reduce((p, a) => {
    if (a.subname) {
      if (!p.hasOwnProperty(a.name)) p[a.name] = {};
      p[a.name][a.subname] = checkValue(value[`${a.subname ? a.subname + '/' : ''}${a.name}`], a.type);
    } else p[a.name] = checkValue(value[a.name], a.type);
    return p;
  }, {});
}

export type ConfigValueTypes = 'structure' | 'string' | 'integer' | 'float' | 'boolean' | 'option' | 'json' | 'map' | 'list' | 'file' | 'text' | 'password';

/**
 * Type casting after form editing
 * Option type may be string | number
 */
export function checkValue(value: string | boolean | object | Array<string> | null, type: ConfigValueTypes) {
  if (value === '' || value === null) return null;

  switch (type) {
    case 'map':
      return Object.keys(value)
        .filter(a => a)
        .reduce((p, c) => {
          p[c] = value[c];
          return p;
        }, {});
    case 'list':
      return (value as Array<string>).filter(a => a);
    case 'structure':
      return value;
  }

  if (typeof value === 'boolean') return value;

  if (typeof value === 'string')
    switch (type) {
      case 'option':
        if (!isNaN(+value)) return parseInt(value, 10);
        else return value;
      case 'integer':
        return parseInt(value, 10);
      case 'float':
        return parseFloat(value);
      case 'json':
        return JSON.parse(value);
      default:
        return value;
    }
}
