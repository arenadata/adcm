import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { AdcmEntity, AdcmTypedEntity } from '../models/entity';
import { TypeName } from '../core/types';

export class EntityHelper {

  static entityToTypedEntity(getter: Observable<AdcmEntity>, typeName: TypeName): Observable<AdcmTypedEntity> {
    return getter.pipe(
      map(entity => ({
        ...entity,
        typeName,
      } as AdcmTypedEntity))
    );
  }

}
