import { IConfigOptions } from './config-options';
export type TValue = string | number | boolean | object | any[];
export type TControlType =
  | 'boolean'
  | 'textbox'
  | 'textarea'
  | 'json'
  | 'password'
  | 'list'
  | 'map'
  | 'dropdown'
  | 'file'
  | 'text'
  | 'structure';

export interface IValidatorInfo {
  pattern?: string | RegExp;
  required?: boolean;
  max?: number;
  min?: number;
}

export interface IVariantSet {
  name?: string;
  strict: boolean;
  type: 'config' | 'inline';
  value: string[];
}

export type TStateType = 'created' | 'locked';

export interface ILimits {
  min?: number;
  max?: number;
  option?: any;
  read_only?: TStateType[];
  yspec?: any; // IYspec;
  rules?: any;
  active?: boolean;
  source?: IVariantSet;
}

export interface ICompare {
  id: number;
  date: string;
  value: string;
  color: string;
}

export interface IFieldOptions extends IConfigOptions {
  default: TValue;
  value: TValue;
  controlType: TControlType;
  validator: IValidatorInfo;
  limits?: ILimits;
  compare: ICompare[];
}
