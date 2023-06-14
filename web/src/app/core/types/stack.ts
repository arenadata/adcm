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
export interface StackBase {
  id: number;
  name: string;
  url: string;
  version: string;
  edition: string;
  description: string;
  display_name: string;
  license: 'unaccepted' | 'accepted' | 'absent';
  bundle_id: number;
  bundle_edition: string;
}

export interface PrototypeListResult {
  count: number;
  next: any;
  previous: any;
  results: PrototypeList[];
}

export interface PrototypeList {
  display_name: string;
  versions: Version[];
}

export interface Version {
  prototype_id: number;
  version: string;
}

export type Prototype = StackBase & {bundle_id: number};
export type ServicePrototype = StackBase & {selected: boolean};
