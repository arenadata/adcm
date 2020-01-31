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
// limitations under the License.s
import { YspecService, IField } from './yspec.service';

const mockField: IField = {
  name: 'root',
  type: 'string',
  controlType: 'textbox',
  validator: {
    required: false,
    pattern: null
  }
};

describe('YspecService', () => {
  let service: YspecService;

  beforeEach(() => {
    service = new YspecService();
    service.Root = { root: { match: 'list', item: 'string' } };
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('create Root element', () => {
    expect(service.Root.root).toBeDefined();
    expect(service.Root.root.match).toBeDefined();
  });

  it('create Field instance', () => {
    expect(service.createField({ path: ['root'], type: 'string' })).toEqual(mockField);
  });
});
