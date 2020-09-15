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



/**
 * Information about the installed service component on a specific host
 */
export interface HostComponent {
  id: number;
  /** host name */
  host: string;
  host_id: number;
  /** component name */
  component: string;
  component_display_name: string;
  component_id: number;
  service_id: number;
  service_display_name: string;
  service_name: string;
  service_version: string;
  state: string;
  url: string;
  host_url: string;
  status: number;
  monitoring: 'passive' | 'active';
}

/**
 * A service component that may be installed on hosts in a cluster.
 */
export interface IComponent {
  id: number;
  prototype_id: number;
  service_id: number;
  service_name: string;
  service_state: string;
  name: string;
  display_name: string;
  status: number;
  constraint: any;
  monitoring?: 'passive' | 'active'; // status page
  requires?: IRequires[];
}

export interface IRequires {
  // id: number;
  prototype_id: number;
  name: string;
  display_name: string;
  components?: IRequires[];
}
