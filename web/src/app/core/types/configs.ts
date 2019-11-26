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

export interface UIoptions {
  invisible?: boolean;
  no_confirm?: boolean;
  advanced?: boolean;
}

interface ValidatorInfo {
  pattern?: string | RegExp;
  required?: boolean;
  max?: number;
  min?: number;
}

/**
 * Property config object from backend
 */
export interface FieldStack {
  type: string;
  name: string;
  display_name: string;
  subname: string;
  default: null | string | number | boolean;
  value: null | string | number | boolean;
  required: boolean;
  description: string;
  limits: {
    min?: number;
    max?: number;
    option?: any;
  };
  read_only: boolean;
  hidden: boolean;
  ui_options?: UIoptions;
  activatable: boolean;
}

/**
 * The object for config for backend
 */
export interface IConfig {
  id?: number;
  date?: Date;
  description?: string;
  config: FieldStack[];
  attr?: { [group: string]: { active: boolean } };
}

/**
 * For Material form controls 
 */
export interface FieldOptions {
  value: string | number | boolean | object | string[] | null;
  //display_name: string;
  key: string;
  label: string;
  required?: boolean;
  order?: number;
  controlType: string;
  type: string;
  description?: string;
  validator: ValidatorInfo;
  disabled?: boolean;
  limits: any;
  hidden: boolean;
  name: string;
  subname: string;
  ui_options?: UIoptions;
  read_only: boolean;
}
