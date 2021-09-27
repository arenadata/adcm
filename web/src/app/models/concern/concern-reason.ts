export enum ConcernEventType {
  Cluster = 'cluster-concerns',
  Service = 'cluster-object-concerns',
  Host = 'host-concerns',
  HostProvider = 'host-provider-concerns',
  ServiceComponent = 'service-component-concerns',
}

export enum IMPlaceholderItemType {
  ComponentActionRun = 'component_action_run',
  ComponentConfig = 'component_config',
  Cluster = 'cluster',
  Service = 'service',
  Component = 'component',
  HostProvider = 'provider',
  Host = 'host',
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

export interface IMPlaceholder {
  [itemKey: string]: IMPlaceholderItem;
}

export interface ConcernReason {
  message: string;
  placeholder: IMPlaceholder;
}
