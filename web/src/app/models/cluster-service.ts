import { IComponent } from './component';
import { BaseEntity } from '@app/core/types';

export interface IClusterService extends BaseEntity {
  bind: string;
  cluster_id: number;
  component: string;
  components: IComponent[];
  imports: string;
  monitoring: string;
  prototype: string;
  version: string;
}
