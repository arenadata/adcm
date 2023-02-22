import { Entity } from '@app/adwp';

export type RbacRoleParametrizedBy = 'cluster' | 'service' | 'component' | 'provider' | 'host';
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
  child: Pick<RbacRoleModel, 'id' | 'name' | 'category' | 'url'>[];
  url: string;
}
