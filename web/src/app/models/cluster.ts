import { BaseEntity } from '@app/core/types';

export interface ICluster extends BaseEntity {
  bind: string;
  edition: string;
  host: string;
  hostcomponent: string;
  imports: string;
  license: string;
  name: string;
  prototype: string;
  service: string;
  serviceprototype: string;
  status_url: string;
  upgradable: boolean;
  upgrade: string;
  group_config: string;
}
