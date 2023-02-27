import { Entity } from '@app/adwp';
import { TypeName } from '@app/core/types';

export interface AdcmEntity extends Entity {
  name?: string;
  display_name?: string;
  fqdn?: string;
}

export interface AdcmTypedEntity extends AdcmEntity {
  typeName: TypeName;
}
