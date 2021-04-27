import { IAction } from './action';
import { IssueEntity } from '@app/models/issue';

export interface ICluster extends IssueEntity {
  action: string;
  actions: IAction[];
  bind: string;
  bundle_id: number;
  config: string;
  description: string;
  edition: string;
  host: string;
  hostcomponent: string;
  imports: string;
  license: string;
  name: string;
  prototype: string;
  prototype_display_name: string;
  prototype_id: number;
  prototype_name: string;
  prototype_version: string;
  service: string;
  serviceprototype: string;
  state: string;
  status: number;
  status_url: string;
  upgradable: boolean;
  upgrade: string;
  url: string;
}
