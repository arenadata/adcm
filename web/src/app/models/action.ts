export interface IActionConfig {
  attr: any;
  config: any[];
}

export interface IAction {
  button: any;
  config: IActionConfig;
  display_name: string;
  hostcomponentmap: any[];
  name: string;
  run: string;
}
