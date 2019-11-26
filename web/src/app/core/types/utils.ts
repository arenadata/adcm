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
 * For lists
 * @field `cmd: string` - command name
 * @field `row: any` - data model from row of list
 * @field `item?: any` - any transmitted object of additionally
 */
export interface EmmitRow {
  cmd: string;
  row: any;
  item?: any;
}

export interface SelectOption {
  id: number | string;
  name: string;
}

export interface IError {
  code: string;
  desc: string;
  level: string;
}
