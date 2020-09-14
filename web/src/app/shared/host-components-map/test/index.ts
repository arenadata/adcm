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
import { IRawHosComponent } from '../types';

export const hc = [
    {
      id: 1,
      host_id: 2,
      service_id: 2,
      component_id: 4,
    },
    {
      id: 2,
      host_id: 2,
      service_id: 2,
      component_id: 2,
    },
    {
      id: 3,
      host_id: 2,
      service_id: 2,
      component_id: 3,
    },
    {
      id: 4,
      host_id: 2,
      service_id: 1,
      component_id: 1,
    },
  ];
 export const raw: IRawHosComponent = {
    hc: [],
    host: [
      {
        state: 'created',
        cluster_id: 2,
        fqdn: 'bbb',
        id: 2,
        prototype_id: 18,
        provider_id: 1,
      },
    ],
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
        monitoring: 'active',
        status: 16,
        service_id: 1,
        service_name: 'GETTAXI',
        service_state: 'created',
      },
      {
        id: 2,
        name: 'UBER_SERVER',
        prototype_id: 38,
        display_name: 'UBER_SERVER',
        constraint: [1, 2],
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
        monitoring: 'active',
        status: 16,
        service_id: 2,
        service_name: 'UBER',
        service_state: 'created',
      },
      {
        id: 3,
        name: 'UBER_NODE',
        prototype_id: 39,
        display_name: 'Simple Uber node',
        constraint: [0, '+'],
        requires: null,
        monitoring: 'active',
        status: 16,
        service_id: 2,
        service_name: 'UBER',
        service_state: 'created',
      },
      {
        id: 4,
        name: 'SLAVE',
        prototype_id: 40,
        display_name: 'Just slave',
        constraint: [0, 1],
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
        monitoring: 'active',
        status: 16,
        service_id: 2,
        service_name: 'UBER',
        service_state: 'created',
      },
    ],
  };

export class HostComponent {
  id: number;
  host_id: number;
  service_id: number;
  component_id: number;
}
