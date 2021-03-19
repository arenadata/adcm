import { AdcmEntity } from '@app/models/entity';

export type IssueType = 'cluster' | 'service' | 'service-component';

export interface IssueEntity extends AdcmEntity {
  issue: IIssues;
}

export interface IIssues {
  config: boolean;
  required_import?: boolean;
  host_component: false;
  cluster?: IssueEntity[];
  service?: IssueEntity[];
}
