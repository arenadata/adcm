import { Observable } from 'rxjs';

import { StatusTree, StatusTreeSubject } from '../models/status-tree';
import { EntityService } from '@app/abstract/entity-service';
import { AdcmEntity } from '@app/models/entity';

export abstract class HavingStatusTreeAbstractService<StatusTreeType extends StatusTreeSubject, EntityType extends AdcmEntity> extends EntityService<EntityType> {

  abstract getStatusTree(id: number): Observable<StatusTreeType>;
  abstract entityStatusTreeToStatusTree(input: StatusTreeType, ...args): StatusTree[];

}
