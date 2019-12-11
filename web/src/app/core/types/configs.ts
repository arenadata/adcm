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

export type stateType = 'created' | 'locked';

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
    read_only: stateType[];
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

export interface ConfigOptions {
  label: string;
  name: string;
  hidden: boolean;
  read_only: boolean;
  ui_options?: UIoptions;
  description?: string;
}

export interface PanelOptions extends ConfigOptions { 
  options: FieldOptions[];  
  activatable?: boolean;
}

/**
 * For Material form controls 
 */
export interface FieldOptions extends ConfigOptions {
  key: string;
  subname: string;
  value: string | number | boolean | object | string[] | null;
  controlType: string;
  type: string;
  validator: ValidatorInfo;
  disabled?: boolean;
  limits: any;
  required: boolean;
}
