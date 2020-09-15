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

export const raw = {
  component: [
    {
      id: 1,
      name: 'NODE',
      prototype_id: 41,
      display_name: 'Taxi Node',
      constraint: null,
      requires: [
        {
          prototype_id: 20,
          name: 'UBER',
          display_name: 'Uber Taxi Service',
          components: [
            {
              prototype_id: 38,
              name: 'UBER_SERVER',
              display_name: 'UBER_SERVER',
            },
            {
              prototype_id: 40,
              name: 'SLAVE',
              display_name: 'Just slave',
            },
            {
              prototype_id: 39,
              name: 'UBER_NODE',
              display_name: 'Simple Uber node',
            },
          ],
        },
      ],
    },
    {
      id: 2,
      name: 'UBER_SERVER',
      prototype_id: 38,
      display_name: 'UBER_SERVER',
      requires: [
        {
          prototype_id: 20,
          name: 'UBER',
          display_name: 'Uber Taxi Service',
          components: [
            {
              prototype_id: 40,
              name: 'SLAVE',
              display_name: 'Just slave',
            },
            {
              prototype_id: 39,
              name: 'UBER_NODE',
              display_name: 'Simple Uber node',
            },
          ],
        },
        {
          prototype_id: 21,
          name: 'GETTAXI',
          display_name: 'GETTAXI',
          components: [
            {
              prototype_id: 41,
              name: 'NODE',
              display_name: 'Taxi Node',
            },
          ],
        },
      ],
    },
    {
      id: 3,
      name: 'UBER_NODE',
      prototype_id: 39,
      display_name: 'Simple Uber node',
      requires: null,
    },
    {
      id: 4,
      name: 'SLAVE',
      prototype_id: 40,
      requires: [
        {
          prototype_id: 21,
          name: 'GETTAXI',
          display_name: 'GETTAXI',
          components: [
            {
              prototype_id: 41,
              name: 'NODE',
              display_name: 'Taxi Node',
            },
          ],
        },
        {
          prototype_id: 20,
          name: 'UBER',
          display_name: 'Uber Taxi Service',
          components: [
            {
              prototype_id: 38,
              name: 'UBER_SERVER',
              display_name: 'UBER_SERVER',
            },
          ],
        },
      ],
    },
  ],
};

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
  constraint: TConstraint = null;
  requires: IRequires[];
  constructor(public id: number, public service_id: number) {
    this.name = `component_${id}`;
    this.display_name = `component_display_name_${id}`;
    this.service_name = `service_${service_id}`;
  }
}

export const ComponentFactory = (count: number, service_id: number) =>
  newArray<IComponent>(count, (_, i) => new HCmComponent(i + 1, service_id) as IComponent);

export const HCFactory = (host_id: number, service_id: number, components: number): Post[] =>
  newArray(components, (_, i) => new Post(host_id, service_id, i + 1, i + 1));
