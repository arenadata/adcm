import { Entity } from '@adwp-ui/widgets';

export interface IIssue extends Entity {
  issue?: IIssue;
  config: boolean;
  required_import: boolean;
  name?: string;
}

export interface IIssues {
  [key: string]: IIssue[];
}
