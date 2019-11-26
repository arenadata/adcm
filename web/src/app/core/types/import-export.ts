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

export interface IExport {
  id: { [key: string]: number };
  bind_id: number | null;
  obj_name: string;
  bundle_name: string;
  bundle_version: string;
  binded: boolean;
}

/** Model for import the configuration of cluster or service */
export interface IImport {
  id: number;
  name: string;
  required: boolean;
  multibind: boolean;
  exports: IExport[];
}
