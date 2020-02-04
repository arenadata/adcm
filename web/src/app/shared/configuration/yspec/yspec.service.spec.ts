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
import { YspecService, IField } from './yspec.service';
import { IYspec } from '../YspecStructure';
import { getPattern } from '@app/core/types';

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

  xit('create List', () => {
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
      type: 'dict',
      country_code: [
        {
          country: {
            name: 'country',
            type: 'string',
            controlType: 'textbox',
            path: ['country_code', 'country'],
            validator: {
              required: false,
              pattern: null
            }
          }
        },
        {
          code: {
            name: 'code',
            type: 'integer',
            controlType: 'textbox',
            path: ['country_code', 'code'],
            validator: {
              required: false,
              pattern: getPattern('integer')
            }
          }
        }
      ]
    };

    expect(service.build()).toEqual(output);
  });
});
