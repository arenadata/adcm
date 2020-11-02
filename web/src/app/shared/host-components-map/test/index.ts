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
import { IComponent, IRequires } from '@app/core/types';
import { newArray } from '@app/core/types/func';

import { Post, TConstraint } from '../types';

export class HCmRequires implements IRequires {
  name: string;
  display_name: string;
  components?: IRequires[];
  constructor(public prototype_id: number) {
    this.name = `name_${prototype_id}`;
    this.display_name = `component_display_name_${prototype_id}`;
  }
}

export class HostComponent {
  id: number;
  host_id: number;
  service_id: number;
  component_id: number;
}

export class HcmHost {
  constructor(public fqdn: string, public id: number) {}
}

export class HCmComponent {
  name: string;
  display_name: string;
  service_name: string;
  service_state = 'created';
  prototype_id: number;
  constraint: TConstraint = null;
  requires: HCmRequires[];
  constructor(public id: number, public service_id: number) {
    this.prototype_id = id;
    this.name = `component_${id}`;
    this.display_name = `component_display_name_${id}`;
    this.service_name = `service_${service_id}`;
  }
}

/**
 * Array with specific service id and components with id by index [1, count]
 * see: class HCmComponent
*/
export const ComponentFactory = (count: number, service_id: number): IComponent[] =>
  newArray<IComponent>(count, (_, i) => new HCmComponent(i + 1, service_id) as IComponent);

export const HCFactory = (host_id: number, service_id: number, components: number): Post[] =>
  newArray(components, (_, i) => new Post(host_id, service_id, i + 1, i + 1));
