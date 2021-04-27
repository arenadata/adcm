import { IComponent } from './component';
import { IssueEntity } from './issue';

export interface IClusterService extends IssueEntity {
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
  monitoring: string;
  prototype: string;
  prototype_id: number;
  state: string;
  status: number;
  url: string;
  version: string;
}
