export enum IMPlaceholderItemType {
  ComponentActionRun = 'component_action_run',
  ComponentConfig = 'component_config',
}

export interface IMPlaceholderItem {
  type: IMPlaceholderItemType;
  name: string;
   ids: { [id: string]: number };
}

export interface IMPlaceholderAction extends IMPlaceholderItem {
  type: IMPlaceholderItemType.ComponentActionRun;
  ids: {
    cluster: number;
    service: number;
    component: number;
    action: number;
  };
}

export interface IMPlaceholderComponent extends IMPlaceholderItem {
  type: IMPlaceholderItemType.ComponentConfig;
  ids: {
    cluster: number;
    service: number;
    component: number;
  };
}

export interface IMPlaceholder {
  [itemKey: string]: IMPlaceholderItem;
}

export interface IssueMessage {
  message: string;
  id: number;
  placeholder: IMPlaceholder;
}
