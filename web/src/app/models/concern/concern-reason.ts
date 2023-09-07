export enum ConcernEventType {
  Cluster = 'cluster-concerns',
  Service = 'cluster-object-concerns',
  Host = 'host-concerns',
  HostProvider = 'host-provider-concerns',
  ServiceComponent = 'service-component-concerns',
}

export enum CauseType {
  Config = 'config',
  Job = 'job',
  HostComponent = 'host-component',
  Import = 'import',
  Service = 'service',
}

export enum IMPlaceholderItemType {
  ComponentActionRun = 'component_action_run',
  ComponentConfig = 'component_config',
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  HostProvider = 'provider',
  Flag = 'flag',
  Host = 'host',
  Job = 'job',
}

export interface IMPlaceholderItem {
  name: string;
  params: {
    [id: string]: number;
  };
  type?: IMPlaceholderItemType;
}

export interface IMPlaceholderActionRun extends IMPlaceholderItem {
  type: IMPlaceholderItemType.ComponentActionRun;
  ids: {
    cluster: number;
    service: number;
    component: number;
    action: number;
  };
}

export interface IMPlaceholderComponentConfig extends IMPlaceholderItem {
  type: IMPlaceholderItemType.ComponentConfig;
  ids: {
    cluster: number;
    service: number;
    component: number;
  };
}

export interface IMPlaceholderCluster extends IMPlaceholderItem {
  type: IMPlaceholderItemType.Cluster;
  ids: {
    cluster: number;
  };
}

export interface IMPlaceholderService extends IMPlaceholderItem {
  type: IMPlaceholderItemType.Service;
  ids: {
    cluster: number;
    service: number;
  };
}

export interface IMPlaceholderComponent extends IMPlaceholderItem {
  type: IMPlaceholderItemType.Component;
  ids: {
    cluster: number;
    service: number;
    component: number;
  };
}

export interface IMPlaceholderHostProvider extends IMPlaceholderItem {
  type: IMPlaceholderItemType.HostProvider;
  ids: {
    provider: number;
  };
}

export interface IMPlaceholderHost extends IMPlaceholderItem {
  type: IMPlaceholderItemType.Host;
  ids: {
    host: number;
    provider: number;
  };
}

export interface IMPlaceholderJob extends IMPlaceholderItem {
  type: IMPlaceholderItemType.Job;
  ids: number;
}

export interface IMPlaceholder {
  [itemKey: string]: IMPlaceholderItem;
}

export interface ConcernReason {
  message: string;
  placeholder: IMPlaceholder;
}
