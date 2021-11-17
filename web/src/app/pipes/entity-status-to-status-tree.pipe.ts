import { Pipe, PipeTransform } from '@angular/core';

import { StatusTree, StatusTreeSubject } from '@app/models/status-tree';
import { HavingStatusTreeAbstractService } from '../abstract/having-status-tree.abstract.service';
import { AdcmEntity } from '@app/models/entity';

@Pipe({
  name: 'entityStatusToStatusTree'
})
export class EntityStatusToStatusTreePipe implements PipeTransform {

  transform<StatusTreeType extends StatusTreeSubject, EntityType extends AdcmEntity>(
    value: StatusTreeType,
    entityService: HavingStatusTreeAbstractService<StatusTreeType, EntityType>,
    data: any,
  ): StatusTree[] {
    return value ? entityService.entityStatusTreeToStatusTree(value, data) : [];
  }

}
