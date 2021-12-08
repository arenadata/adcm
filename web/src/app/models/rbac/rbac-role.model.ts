import { Entity } from '@adwp-ui/widgets';

export interface RbacRoleModel extends Entity {
  name: string;
  description: string;
  built_in: boolean;
  business_permit: boolean;
  category: unknown[];
  parametrized_by_type: unknown[];
  child: unknown[];
  url: string;
}
