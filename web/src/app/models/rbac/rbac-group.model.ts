import { Entity } from '@adwp-ui/widgets';

export interface RbacGroupModel extends Entity {
  name: string;
  description: string;
  user: unknown[];
  url: string;
}
