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
import { IYspec } from './yspec/yspec.service';

export type stateType = 'created' | 'locked';

export type ConfigValueTypes =
  | 'structure'
  | 'group'
  | 'dict'
  | 'string'
  | 'integer'
  | 'int'
  | 'float'
  | 'boolean'
  | 'option'
  | 'json'
  | 'map'
  | 'list'
  | 'file'
  | 'text'
  | 'password';
export type simpleTypes = string | number | boolean;
export type ConfigResultTypes = simpleTypes | simpleTypes[] | object | null;

export interface UIoptions {
  invisible?: boolean;
  no_confirm?: boolean;
  advanced?: boolean;
}

export interface ILimits {
  min?: number;
  max?: number;
  option?: any;
  read_only?: stateType[];
  yspec?: IYspec;
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
  type: ConfigValueTypes;
  name: string;
  display_name: string;
  subname: string;
  default: null | string | number | boolean | object | any[];
  value: null | string | number | boolean;
  required: boolean;
  description: string;
  limits?: ILimits;
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
  date?: string;
  description?: string;
  config: FieldStack[];
  attr?: { [group: string]: { active: boolean } };
}

export interface ConfigOptions {
  key?: string;
  type: ConfigValueTypes;
  display_name: string;
  name: string;
  subname: string;
  hidden: boolean;
  read_only: boolean;
  ui_options?: UIoptions;
  description?: string;
}

export interface PanelOptions extends ConfigOptions {
  options: (FieldOptions | PanelOptions)[];
  activatable?: boolean;
}

export interface CompareConfig extends IConfig {
  color: string;
}

interface Compare {
  id: number;
  date: string;
  value: string;
  color: string;
}

/**
 * For Material form controls
 */
export interface FieldOptions extends ConfigOptions {
  default: null | string | number | boolean | object | any[];
  value: string | number | boolean | object | string[] | null;
  controlType: string;
  validator: ValidatorInfo;
  disabled?: boolean;
  limits?: ILimits;
  compare: Compare[];
}

export interface IStructure extends FieldOptions {
  rules: { [x: string]: any; type: string };
}
