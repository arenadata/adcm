export type TConfigValueTypes =
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
  | 'password'
  | 'variant';

export interface IUIoptions {
  invisible?: boolean;
  no_confirm?: boolean;
  advanced?: boolean;
}

export interface IConfigOptions {
  key?: string;
  type: TConfigValueTypes;
  display_name: string;
  name: string;
  subname: string;
  hidden: boolean;
  read_only: boolean;
  ui_options?: IUIoptions;
  description?: string;
  activatable?: boolean;
  required: boolean;
}
