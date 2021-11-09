import { Pipe, PipeTransform } from '@angular/core';

import { StatusTree, StatusTreeLinkFunc } from '@app/models/status-tree';

@Pipe({
  name: 'statusTreeLink'
})
export class StatusTreeLinkPipe implements PipeTransform {

  transform(id: number, tree: StatusTree[], func: StatusTreeLinkFunc): string[] {
    return func(id, tree);
  }

}
