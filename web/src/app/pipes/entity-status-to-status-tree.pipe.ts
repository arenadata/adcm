import { Pipe, PipeTransform } from '@angular/core';

import { StatusTree, StatusTreeSubject } from '@app/models/status-tree';
import { HavingStatusTreeAbstractService } from '../abstract/having-status-tree.abstract.service';

@Pipe({
  name: 'entityStatusToStatusTree'
})
export class EntityStatusToStatusTreePipe implements PipeTransform {

  transform<StatusTreeType extends StatusTreeSubject>(
    value: StatusTreeType,
    entityService: HavingStatusTreeAbstractService<StatusTreeType>,
  ): StatusTree[] {
    return value ? entityService.entityStatusTreeToStatusTree(value) : [];
  }

}
