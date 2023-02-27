import { Entity } from '@app/adwp';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';

export interface RbacGroupModel extends Entity {
  id: number;
  name: string;
  description: string;
  user: RbacUserModel[];
  url: string;
  built_in: boolean;
  type: string;
}
