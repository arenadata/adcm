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
import { clearEmptyField, nullEmptyField } from './func';

describe('Functions test', () => {


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
