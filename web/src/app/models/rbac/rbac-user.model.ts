import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';
import { IProfile } from '@app/core/store';

export interface RbacUserModel {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  password: string;
  url: string;
  profile: IProfile;
  group: Pick<RbacGroupModel, 'id' | 'name' | 'url'>[];
  built_in: boolean;
  type: string;

  //
  change_password: string;
}
