import { Pipe, PipeTransform } from '@angular/core';

import { HostService } from '@app/services/host.service';
import { HostStatusTree } from '@app/models/status-tree';

@Pipe({
  name: 'hostStatusToStatusTree'
})
export class HostStatusToStatusTreePipe implements PipeTransform {

  constructor(
    private hostService: HostService,
  ) {}

  transform(value: HostStatusTree): unknown {
    return value ? this.hostService.hostStatusTreeToStatusTree(value) : [];
  }

}
