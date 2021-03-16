import { AdcmEntity } from './entity';

export interface IServiceComponent extends AdcmEntity {
  constraint: Array<number | string>;
  description: string;
  monitoring: string;
  prototype_id: number;
  requires: Array<any>;
  status: number;
  url: string;
}
