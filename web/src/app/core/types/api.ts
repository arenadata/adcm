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
import { IAction } from './actions';
import { IComponent } from './host-component';
import { Issue } from './issue';
import { Job, Task } from './task-job';

export type TypeName = 'bundle' | 'cluster' | 'host' | 'provider' | 'service' | 'job' | 'task' | 'user' | 'profile' | 'adcm' | 'stats' | 'hostcomponent' | 'component';
export type Entities = Cluster | Service | Host | Provider | Job | Task | Bundle;

/**
 *```
 {
   [key: string]: string;
 }
 ```
 */
export interface IRoot {
  [key: string]: string;
}

export interface ApiBase {
  typeName: TypeName;
  id: number;
  name: string;
  display_name?: string;
  description?: string;
  url: string;
  state: string;
  config: string;
  action: string;
  actions: IAction[];
  issue: Issue;
  prototype_id: number;
  prototype_name: string;
  prototype_display_name?: string;
  prototype_version: string;
  bundle_id: number;
  status: number | string;
}

export interface Cluster extends ApiBase {
  service: string;
  host: string;
  bundle: string;
  hostcomponent: string;
  imports: string;
  bind: string;
  serviceprototype: string;
  upgradable: boolean;
  upgrade: string;
  status_url: string;
}

export interface Provider extends ApiBase {
  host: string;
}

export interface Host extends ApiBase {
  fqdn: string;
  provider_id: number;
  cluster: string;
  cluster_id?: number;
  cluster_name?: string;
}

export interface Service extends ApiBase {
  components: IComponent[];
  status: number;
  hostcomponent: string;
  display_name: string;
}

export interface Bundle extends ApiBase {
  [key: string]: any;
  license: 'unaccepted' | 'accepted' | 'absent';
  license_url: string;
}
