import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';

export interface RbacUserModel {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  is_superuser: boolean;
  password: string;
  url: string;
  profile: unknown;
  group: Pick<RbacGroupModel, 'id' | 'name' | 'url'>[];
}
