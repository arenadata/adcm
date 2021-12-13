import { Entity } from '@adwp-ui/widgets';

export type RbacRoleParametrizedBy = 'Cluster' | 'Service' | 'Component' | 'Provider' | 'Host';
export type RbacRoleType = 'hidden' | 'business' | 'role';

export interface RbacRoleModel extends Entity {
  id: number;
  name: string;
  description: string;
  display_name: string;
  built_in: boolean;
  type: RbacRoleType;
  category: string[];
  parametrized_by_type: RbacRoleParametrizedBy[];
  child: Pick<RbacRoleModel, 'id' | 'name' | 'url'>[];
  url: string;
}
