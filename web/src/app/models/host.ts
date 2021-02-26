import { Entity } from '@adwp-ui/widgets';
import { IAction } from './action';
import { IIssues } from './issue';

export interface IHost extends Entity {
  action: string;
  actions: IAction[];
  cluster_id?: number;
  cluster_url?: string;
  cluster_name?: string;
  config: string;
  fqdn: string;
  host_id: number;
  host_url: string;
  issue: IIssues;
  monitoring: string;
  prototype_display_name: string;
  prototype_id: number;
  prototype_name: string;
  prototype_version: string;
  provider_id: number;
  provider_name: number;
  state: string;
  status: number;
  upgradable: boolean;
  url: string;
}
