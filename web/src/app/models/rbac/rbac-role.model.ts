import { Entity } from '@adwp-ui/widgets';

export type ParametrizedBy = 'Cluster' | 'Service' | 'Component' | 'Provider' | 'Host';

export interface RbacRoleModel extends Entity {
  name: string;
  description: string;
  built_in: boolean;
  business_permit: boolean;
  category: string[];
  parametrized_by_type: ParametrizedBy[];
  child: unknown[];
  url: string;
}
