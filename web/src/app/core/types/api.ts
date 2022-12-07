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
import { Job, Task } from './task-job';
import { AdcmEntity } from '@app/models/entity';
import { IIssues } from '@app/models/issue';
import { ICluster } from '@app/models/cluster';
import { Concern } from '@app/models/concern/concern';

export type TypeName =
  'bundle' |
  'cluster' |
  'host' |
  'provider' |
  'service' |
  'job' |
  'task' |
  'user' |
  'profile' |
  'adcm' |
  'stats' |
  'hostcomponent' |
  'service2cluster' |
  'host2cluster' |
  'servicecomponent' |
  'component' |
  'group_config' |
  'group_config_hosts' |
  'group' |
  'role' |
  'policy' |
  'audit_operations' |
  'audit_login';
export type Entities = ICluster | Service | Host | Provider | Job | Task | Bundle;

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

export interface BaseEntity extends AdcmEntity {
  typeName: TypeName;
  description?: string;
  url: string;
  state?: string;
  config: string;
  action?: string;
  actions?: IAction[];
  issue?: IIssues;
  prototype_id?: number;
  prototype_name?: string;
  prototype_display_name?: string;
  prototype_version?: string;
  bundle_id?: number;
  status?: number | string;
  concerns: Concern[];
  locked: boolean;
  main_info?: string;
}

export interface ApiFlat {
  id: number;
  object_id: number;
  object_type: TypeName;
  url: string;
}

export interface Provider extends BaseEntity {
  host: string;
}

export interface Host extends BaseEntity {
  fqdn: string;
  provider_id: number;
  provider_name: string;
  cluster: string;
  cluster_id?: number;
  cluster_name?: string;
  maintenance_mode?: string;
}

export interface Service extends BaseEntity {
  components: IComponent[];
  status: number;
  hostcomponent: string;
  display_name: string;
  cluster_id?: number;
  group_config: string;
}

export interface CanLicensed {
  license: 'unaccepted' | 'accepted' | 'absent';
  license_url: string;
}

export interface License {
  accept: string;
  license: 'unaccepted' | 'accepted' | 'absent';
  text: string;
}

export interface Bundle extends BaseEntity, CanLicensed {
  [key: string]: any;
}
