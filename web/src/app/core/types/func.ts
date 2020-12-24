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
export const isBoolean = (x: any) => typeof x === 'boolean';
export const isObject = (x: any) => x !== null && typeof x === 'object';
export const isEmptyObject = (x: any) => isObject(x) && !Object.keys(x).length;
export const isNumber = (x: any) => typeof x === 'number' && !isNaN(x);

export const randomInteger = (max: number, min: number = 0): number =>
  Math.floor(min + Math.random() * (max + 1 - min));

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
 * @deprecated
 */
export function nullEmptyField(input: Object): Object {
  return Object.keys(input).reduce((output, key) => {
    const data = input[key];
    if (isObject(data) && !Array.isArray(data)) {
      // tslint:disable-next-line: deprecation
      output[key] = nullEmptyField(data);
      if (!Object.keys(output[key]).length) delete output[key];
    } else if ((typeof data === 'number' && isNaN(data)) || (typeof data === 'string' && !data) || data === null)
      output[key] = null;
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
  return a.reduce<T[]>((acc, val) => (Array.isArray(val) ? acc.concat(flatten<T>(val as T[])) : acc.concat(val)), []);
}

/**
 *
 *
 * @template T
 * @param {number} count
 * @param {(_: never, i: number) => T} fn
 * @returns
 */
export function newArray<T>(count: number, fn: (_: never, i: number) => T) {
  return Array(count).fill(0).map(fn);
}

/**
 * @returns 16-bit hex string
 * @example '#110C2E'
 */
export function getRandomColor(): string {
  const letters = '0123456789ABCDEF';
  return newArray(6, (_, i) => i).reduce((p) => (p += letters[Math.floor(Math.random() * 16)]), '#');
}

export function uniqid(prefix: string = '', isFloat: boolean = false): string {
  const seed = (s: number, w: number, z = s.toString(16)): string =>
    w < z.length ? z.slice(z.length - w) : w > z.length ? new Array(1 + (w - z.length)).join('0') + z : z;
  let result =
    prefix +
    seed(parseInt((new Date().getTime() / 1000).toString(), 10), 8) +
    seed(Math.floor(Math.random() * 0x75bcd15) + 1, 5);
  if (isFloat) result += (Math.random() * 10).toFixed(8).toString();
  return result;
}
