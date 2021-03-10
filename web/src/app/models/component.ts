import { AdcmEntity } from './entity';

export interface IComponent extends AdcmEntity {
  action: string;
  bound_to: any;
  config: string;
  constraint: Array<number | string>;
  description: string;
  monitoring: string;
  prototype_id: number;
  requires: any[];
  status: number;
  url: string;
}
