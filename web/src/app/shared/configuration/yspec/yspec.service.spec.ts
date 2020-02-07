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
import { getPattern } from '@app/core/types';

import { IField, IYspec, YspecService } from './yspec.service';

const simpleField: IField = {
  name: 'root',
  type: 'string',
  controlType: 'textbox',
  path: ['root'],
  validator: {
    required: false,
    pattern: null
  }
};

const simpleStr: IYspec = {
  root: { match: 'list', item: 'simpl_str' },
  simpl_str: {
    match: 'string'
  }
};

describe('YspecService', () => {
  let service: YspecService;

  beforeEach(() => {
    service = new YspecService();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('create Root element', () => {
    service.Root = simpleStr;
    expect(service.Root.root).toBeDefined();
    expect(service.Root.root.match).toBeDefined();
  });

  it('create Field instance', () => {
    service.Root = simpleStr;
    expect(service.field({ path: ['root'], type: 'string' })).toEqual(simpleField);
  });

  it('simple List with Dict', () => {
    service.Root = {
      root: { match: 'list', item: 'country_code' },
      country_code: {
        match: 'dict',
        items: {
          country: 'str',
          code: 'int'
        }
      },
      str: {
        match: 'string'
      },
      int: {
        match: 'integer'
      }
    };

    const output = {
      type: 'list',
      root: {
        type: 'dict',
        country_code: [
          {
            name: 'country',
            type: 'string',
            controlType: 'textbox',
            path: ['country_code', 'country'],
            validator: {
              required: false,
              pattern: null
            }
          },
          {
            name: 'code',
            type: 'integer',
            controlType: 'textbox',
            path: ['country_code', 'code'],
            validator: {
              required: false,
              pattern: getPattern('integer')
            }
          }
        ]
      }
    };

    const _out = service.build();
    //console.log(_out);
    expect(_out).toEqual(output);
  });

  it('test build function :: dictionary with inner elements', () => {
    service.Root = {
      boolean: { match: 'bool' },
      string: { match: 'string' },
      integer: { match: 'int' },
      float: { match: 'float' },
      list: { match: 'list', item: 'string' },
      onemoredict: { match: 'dict', items: { key1: 'list', key2: 'the_dict' } },
      the_dict: { match: 'dict', items: { key1: 'boolean', key2: 'string', key3: 'integer', key4: 'float', key5: 'list' } },
      root: {
        match: 'dict',
        items: { key1: 'boolean', key2: 'string', key3: 'integer', key4: 'float', key5: 'list', key6: 'onemoredict' }
      }
    };

    const output = {
      type: 'dict',
      root: [
        {
          name: 'key1',
          type: 'bool',
          path: ['key1'],
          controlType: 'boolean',
          validator: { required: false, pattern: getPattern('boolean') }
        },
        {
          name: 'key2',
          type: 'string',
          path: ['key2'],
          controlType: 'textbox',
          validator: { required: false, pattern: getPattern('string') }
        },
        {
          name: 'key3',
          type: 'int',
          path: ['key3'],
          controlType: 'textbox',
          validator: { required: false, pattern: getPattern('int') }
        },
        {
          name: 'key4',
          type: 'float',
          path: ['key4'],
          controlType: 'textbox',
          validator: { required: false, pattern: getPattern('float') }
        },
        {
          type: 'list',
          key5: {
            name: 'string',
            type: 'string',
            path: ['key5', 'string'],
            controlType: 'textbox',
            validator: {
              required: false,
              pattern: getPattern('string')
            }
          }
        },
        {
          type: 'dict',
          key6: [
            {
              type: 'list',
              key1: {
                name: 'string',
                type: 'string',
                path: ['key6', 'key1', 'string'],
                controlType: 'textbox',
                validator: {
                  required: false,
                  pattern: getPattern('string')
                }
              }
            },
            {
              type: 'dict',
              key2: [
                {
                  name: 'key1',
                  type: 'bool',
                  path: ['key6', 'key2', 'key1'],
                  controlType: 'boolean',
                  validator: { required: false, pattern: getPattern('boolean') }
                },
                {
                  name: 'key2',
                  type: 'string',
                  path: ['key6', 'key2', 'key2'],
                  controlType: 'textbox',
                  validator: { required: false, pattern: getPattern('string') }
                },
                {
                  name: 'key3',
                  type: 'int',
                  path: ['key6', 'key2', 'key3'],
                  controlType: 'textbox',
                  validator: { required: false, pattern: getPattern('int') }
                },
                {
                  name: 'key4',
                  type: 'float',
                  path: ['key6', 'key2', 'key4'],
                  controlType: 'textbox',
                  validator: { required: false, pattern: getPattern('float') }
                },
                {
                  type: 'list',
                  key5: {
                    name: 'string',
                    type: 'string',
                    path: ['key6', 'key2', 'key5', 'string'],
                    controlType: 'textbox',
                    validator: {
                      required: false,
                      pattern: getPattern('string')
                    }
                  }
                }
              ]
            }
          ]
        }
      ]
    };

    expect(service.build()).toEqual(output);
  });
});
