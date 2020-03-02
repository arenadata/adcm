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
import { Injectable } from '@angular/core';
import { Cluster, IAction, Issue, TypeName, LogFile, JobObject } from '@app/core/types';

export interface IDetails {
  parent?: Cluster;
  typeName: TypeName;
  id: number;
  name: string;
  upgradable: boolean;
  upgrade: string;
  status: string | number;
  actions: IAction[];
  issue: Issue;
  log_files?: LogFile[];
  objects: JobObject[];
  prototype_name: string;
  prototype_display_name: string;
  prototype_version: string;
  provider_id: number;
  bundle_id: number;
}

@Injectable({
  providedIn: 'root'
})
export class DetailsService {
  constructor() {}
}
