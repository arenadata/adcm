import { Entity } from '@app/adwp';
import { RbacRoleModel } from './rbac-role.model';
import { RbacUserModel } from './rbac-user.model';
import { RbacGroupModel } from './rbac-group.model';

export interface RbacPolicyModel extends Entity {
  id: number;
  name: string;
  description: string;
  object: unknown[];
  built_in: boolean;
  role: Pick<RbacRoleModel, 'id' | 'name' | 'url' | 'parametrized_by_type'>[];
  user: Pick<RbacUserModel, 'id' | 'username' | 'url'>[];
  group: Pick<RbacGroupModel, 'id' | 'name' | 'url'>[];
  url: string;
}
