import { IssueEntity } from '@app/models/issue';
import { IAction } from '@app/models/action';

export interface IServiceComponent extends IssueEntity {
  cluster_id: number;
  service_id: number;
  description: string;
  constraint: Array<number | string>;
  monitoring: string;
  prototype_id: number;
  requires: Array<any>;
  bound_to: any;
  status: number;
  url: string;
  state: string;
  action: string;
  config: string;
  prototype: string;
  actions: IAction[];
  version: string;
}
