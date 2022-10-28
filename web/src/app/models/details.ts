import { ICluster } from './cluster';
import { IAction, JobObject, LogFile, TypeName } from '../core/types';
import { IIssues } from './issue';
import { AdcmTypedEntity } from './entity';

export interface IDetails {
  parent?: ICluster;
  typeName: TypeName;
  id: number;
  name: string;
  upgradable: boolean;
  upgrade: string;
  status: string | number;
  /** link to actionss */
  action: string;
  actions: IAction[];
  issue: IIssues;
  log_files?: LogFile[];
  objects: JobObject[];
  prototype_name: string;
  prototype_display_name: string;
  prototype_version: string;
  provider_id: number;
  provider_name: string;
  bundle_id: number;
  hostcomponent: string;
  state: string;
}

export interface INavItem {
  id?: number;
  title: string;
  url: string;
  issue?: string;
  status?: number;
  statusMessage?: string;
  action?: () => void;
  path?: string;
  name?: string;
}

export interface IStyledNavItem {
  class?: string;
  entity?: AdcmTypedEntity;
}
