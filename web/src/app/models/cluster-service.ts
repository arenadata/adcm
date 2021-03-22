import { IComponent } from './component';
import { AdcmEntity } from './entity';
import { IIssues } from './issue';

export interface IClusterService extends AdcmEntity {
  action: string;
  actions: any[];
  bind: string;
  bundle_id: number;
  cluster_id: number;
  component: string;
  components: IComponent[];
  config: string;
  description: string;
  imports: string;
  issue: IIssues;
  monitoring: string;
  prototype: string;
  prototype_id: number;
  state: string;
  status: number;
  url: string;
  version: string;
}
