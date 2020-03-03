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
import { IYContainer, IYField, IYspec, YspecService } from './yspec.service';

const simpleField: IYField = {
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

  it('Root as list of dict', () => {
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

    const output: IYContainer = {
      name: 'root',
      type: 'list',
      options: {
        type: 'dict',
        name: 'country_code',
        options: [
          {
            name: 'country',
            type: 'string',
            path: ['country', 'country_code'],
            controlType: 'textbox',
            validator: { required: false, pattern: null }
          },
          {
            name: 'code',
            type: 'integer',
            path: ['code', 'country_code'],
            controlType: 'textbox',
            validator: { required: false, pattern: /^[-]?\d+$/ }
          }
        ]
      }
    };

    const _out = service.build();
    //console.log(_out);
    expect(_out).toEqual(output);
  });

  it('Scheme as tree :: dictionary with inner elements', () => {
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

    const output: IYContainer = {
      name: 'root',
      type: 'dict',
      options: [
        {
          name: 'key1',
          type: 'bool',
          path: ['key1'],
          controlType: 'boolean',
          validator: { required: false, pattern: null }
        },
        {
          name: 'key2',
          type: 'string',
          path: ['key2'],
          controlType: 'textbox',
          validator: { required: false, pattern: null }
        },
        {
          name: 'key3',
          type: 'int',
          path: ['key3'],
          controlType: 'textbox',
          validator: { required: false, pattern: /^[-]?\d+$/ }
        },
        {
          name: 'key4',
          type: 'float',
          path: ['key4'],
          controlType: 'textbox',
          validator: { required: false, pattern: /^[-]?[0-9]+(\.[0-9]+)?$/ }
        },
        {
          type: 'list',
          name: 'key5',
          options: {
            name: 'string',
            type: 'string',
            path: ['string', 'key5'],
            controlType: 'textbox',
            validator: {
              required: false,
              pattern: null
            }
          }
        },
        {
          type: 'dict',
          name: 'key6',
          options: [
            {
              type: 'list',
              name: 'key1',
              options: {
                name: 'string',
                type: 'string',
                path: ['string', 'key1', 'key6'],
                controlType: 'textbox',
                validator: {
                  required: false,
                  pattern: null
                }
              }
            },
            {
              type: 'dict',
              name: 'key2',
              options: [
                {
                  name: 'key1',
                  type: 'bool',
                  path: ['key1', 'key2', 'key6'],
                  controlType: 'boolean',
                  validator: { required: false, pattern: null }
                },
                {
                  name: 'key2',
                  type: 'string',
                  path: ['key2', 'key2', 'key6'],
                  controlType: 'textbox',
                  validator: { required: false, pattern: null }
                },
                {
                  name: 'key3',
                  type: 'int',
                  path: ['key3', 'key2', 'key6'],
                  controlType: 'textbox',
                  validator: { required: false, pattern: /^[-]?\d+$/ }
                },
                {
                  name: 'key4',
                  type: 'float',
                  path: ['key4', 'key2', 'key6'],
                  controlType: 'textbox',
                  validator: { required: false, pattern: /^[-]?[0-9]+(\.[0-9]+)?$/ }
                },
                {
                  type: 'list',
                  name: 'key5',
                  options: {
                    name: 'string',
                    type: 'string',
                    path: ['string', 'key5', 'key2', 'key6'],
                    controlType: 'textbox',
                    validator: {
                      required: false,
                      pattern: null
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
