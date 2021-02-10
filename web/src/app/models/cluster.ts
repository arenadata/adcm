import { IAction } from './action';
import { AdcmEntity } from '@app/models/entity';

export interface ICluster extends AdcmEntity {
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
  issue: any;
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
