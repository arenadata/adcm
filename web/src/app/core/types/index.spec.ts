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
import { checkValue, clearEmptyField, nullEmptyField } from './func';

describe('Test app/core/types/func', () => {

  it('function [checkValue - "", "string"] should return 2', () => {
    expect(checkValue('', 'string')).toBe(null);
  });

  it('function [checkValue - 2.0, "float"] should return 2', () => {
    expect(checkValue('2.0', 'float')).toBe(2);
  });

  it('function [checkValue - 2.2, "float"] should return 2.2', () => {
    expect(checkValue('2.2', 'float')).toBe(2.2);
  });

  it('function [checkValue - "0", "float"] should return 0', () => {
    expect(checkValue('0', 'float')).toBe(0);
  });

  it('function [checkValue - "", "float"] should return null', () => {
    expect(checkValue('', 'float')).toBe(null);
  });

  it('function [checkValue - 23456778, "integer"] should return 23456778', () => {
    expect(checkValue('23456778', 'integer')).toBe(23456778);
  });

  it('function [checkValue - "0", "integer"] should return 0', () => {
    expect(checkValue('0', 'integer')).toBe(0);
  });

  it('function [checkValue - "", "integer"] should return null', () => {
    expect(checkValue('', 'integer')).toBe(null);
  });

  it('function [checkValue - "12345678", "option"] should return 12345678', () => {
    expect(checkValue('12345678', 'option')).toBe(12345678);
  });

  it('function [checkValue - "default", "option"] should return "default"', () => {
    expect(checkValue('default', 'option')).toBe('default');
  });

  it('function [checkValue - "0 one two", "option"] should return "0 one two"', () => {
    expect(checkValue('0 one two', 'option')).toBe('0 one two');
  });

  it('function [checkValue - "0", "option"] should return 0', () => {
    expect(checkValue('0', 'option')).toBe(0);
  });

  it('function [checkValue - "", "option"] should return null', () => {
    expect(checkValue('', 'option')).toBe(null);
  });


  it('function [checkValue - true, "boolean"] should return true', () => {
    expect(checkValue(true, 'boolean')).toBe(true);
  });

  it('function [checkValue - false, "boolean"] should return false', () => {
    expect(checkValue(false, 'boolean')).toBe(false);
  });

  it('function [checkValue - null, "boolean"] should return null', () => {
    expect(checkValue(null, 'boolean')).toBe(null);
  });

  it('function [checkValue - {}, "json"] should return {}', () => {
    expect(checkValue('{}', 'json')).toEqual({});
  });

  it('function [checkValue - "", "json"] should return null', () => {
    expect(checkValue('', 'json')).toEqual(null);
  });

  it('function [checkValue - "null", "json"] should return null', () => {
    expect(checkValue('null', 'json')).toEqual(null);
  });

  it('function [checkValue - "{↵    "a": 23 ↵}", "json"] should return { "a": 23 }', () => {
    expect(checkValue('{"a": 23 }', 'json')).toEqual({'a': 23});
  });

  it('function [clearEmptyField] should return', () => {
    expect(
      clearEmptyField({
        int: 2,
        float_zero: 2.0,
        float: 2.1,
        str: '0abs',
        bool_false: false,
        bool_true: true,
        nul: null,
        empty: '',
        empty_object: { a: null },
        json: {
          a: null,
          b: 'b',
          c: 123,
          d: '',
          e: [{ a: 1 }, {}, { b: 2 }, { c: null }, { k: ['a', 0, 1, null, false] }],
          k: ['a', 0, 1, null, false],
        },
      })
    ).toEqual({
      int: 2,
      float_zero: 2,
      float: 2.1,
      str: '0abs',
      bool_false: false,
      bool_true: true,
      json: {
        b: 'b',
        c: 123,
        e: [{ a: 1 }, {}, { b: 2 }, { c: null }, { k: ['a', 0, 1, null, false] }],
        k: ['a', 0, 1, null, false],
      },
    });
  });

  it('function [nullEmptyField] should return', () => {
    expect(
      nullEmptyField({
        int: 2,
        int_o: 0,
        float_zero: 2.0,
        float: 2.1,
        float_o: 0,
        str: '0abs',
        bool_false: false,
        bool_true: true,
        bool_null: null,
        nul: null,
        empty: '',
        empty_object: { a: null },
        json: {
          a: null,
          b: 'b',
          c: 123,
          d: '',
          e: [{ a: 1 }, {}, { b: 2 }, { c: null }, { k: ['a', 0, 1, null, false] }],
          k: ['a', 0, 1, null, false],
        },
      })
    ).toEqual({
      int: 2,
      int_o: 0,
      float_zero: 2.0,
      float: 2.1,
      float_o: 0,
      str: '0abs',
      bool_false: false,
      bool_true: true,
      bool_null: null,
      nul: null,
      empty: null,
      empty_object: { a: null },
      json: {
        a: null,
        b: 'b',
        c: 123,
        d: null,
        e: [{ a: 1 }, {}, { b: 2 }, { c: null }, { k: ['a', 0, 1, null, false] }],
        k: ['a', 0, 1, null, false],
      },
    });
  });
});
