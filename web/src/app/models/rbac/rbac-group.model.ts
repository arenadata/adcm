import { Entity } from '@adwp-ui/widgets';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';

export interface RbacGroupModel extends Entity {
  name: string;
  description: string;
  user: RbacUserModel[];
  url: string;
}
