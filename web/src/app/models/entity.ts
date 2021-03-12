import { Entity } from '@adwp-ui/widgets';
import { TypeName } from '@app/core/types';

export interface AdcmEntity extends Entity {
  name?: string;
  display_name?: string;
}

export interface AdcmTypedEntity extends AdcmEntity {
  typeName: TypeName;
}
