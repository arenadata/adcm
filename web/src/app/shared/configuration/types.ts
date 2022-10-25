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
import { TFormOptions } from './services/field.service';
import { BaseEntity } from '@app/core/types';

export type stateType = 'created' | 'locked';

export type TNBase = 'string' | 'integer' | 'int' | 'boolean' | 'bool' | 'float';
export type TNReq = 'dict' | 'list';
export type TNSpec = 'structure' | 'group' | 'option' | 'json' | 'map' | 'file' | 'text' | 'password' | 'secrettext' | 'variant';
export type TNForm = TNBase | TNReq | TNSpec;
export type simpleTypes = string | number | boolean;
export type resultTypes = simpleTypes | simpleTypes[] | object;
export type TValue = string | number | boolean | object | any[];

/**
 *```
 {
    invisible?: boolean;
    no_confirm?: boolean;
    advanced?: boolean;
 }
 ```
 *
 */
export interface IUIoptions {
  invisible?: boolean;
  no_confirm?: boolean;
  advanced?: boolean;
}

/**
 * ```
 {
    min?: number;
    max?: number;
    option?: any;
    read_only?: stateType[];   // created | locked
    yspec?: IYspec;
    rules?: any;
    active?: boolean;
}
 * ```
 */
export interface IVariantSet {
  name?: string;
  strict: boolean;
  type: 'config' | 'inline';
  value: string[];
}

export interface ILimits {
  min?: number;
  max?: number;
  option?: any;
  read_only?: stateType[];
  yspec?: IYspec;
  rules?: any;
  active?: boolean;
  source?: IVariantSet;
}

/**
 * Property config object from backend
 */
export interface IFieldStack {
  name: string;
  subname: string;
  display_name: string;
  type: TNForm;
  default: TValue;
  value: TValue;
  required: boolean;
  activatable: boolean;
  read_only: boolean;
  description?: string;
  custom_group?: boolean;
  limits?: ILimits;
  ui_options?: IUIoptions;
  group_config?: { [key: string]: boolean };
}

/**
 * The object for config for backend
 */
export interface IConfig {
  id?: number;
  date?: string;
  description?: string;
  config: IFieldStack[];
  attr?: IConfigAttr;
  obj_ref?: number;
}

/**
 *```
 {
    [group: string]: { active: boolean };
}
 ```
 */
export interface IConfigAttr {
  [group: string]: { active?: boolean };

  group_keys?: { [key: string]: { [key: string]: boolean }};
  custom_group_keys?: { [key: string]: { [key: string]: boolean }};
}

//#region Modified data for ngForm build

/**
 * Mark for rendering required component
 */
export type controlType =
  'boolean'
  | 'textbox'
  | 'textarea'
  | 'json'
  | 'password'
  | 'list'
  | 'map'
  | 'dropdown'
  | 'file'
  | 'text'
  | 'structure'
  | 'secrettext';

/**
 *```
 pattern?: string | RegExp;
 required?: boolean;
 max?: number;
 min?: number;
 ```
 */
export interface IValidator {
  pattern?: string | RegExp;
  required?: boolean;
  max?: number;
  min?: number;
}

export interface CompareConfig extends IConfig {
  color: string;
}

export interface ICompare {
  id: number;
  date: string;
  value: string;
  color: string;
}

export interface IFormOptions extends IFieldStack {
  key?: string;
  hidden: boolean;
}

export interface IPanelOptions extends IFormOptions {
  options: TFormOptions[];
  active: boolean;
}

export interface ICanGroup {
  group?: boolean;
}

export interface IFieldOptions extends IFormOptions, ICanGroup {
  controlType: controlType;
  validator: IValidator;
  compare: ICompare[];
}

export interface ISettingsListResponse {
  count: 1;
  next: null;
  previous: null;
  results: BaseEntity[];
}

//#endregion
