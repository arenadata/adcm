import { Pipe, PipeTransform } from '@angular/core';

import { ClusterStatusTree, StatusTree } from '@app/models/status-tree';
import { ClusterEntityService } from '../services/cluster-entity.service';

@Pipe({
  name: 'clusterStatusToStatusTree'
})
export class ClusterStatusToStatusTreePipe implements PipeTransform {

  constructor(
    private clusterEntityService: ClusterEntityService,
  ) {}

  transform(value: ClusterStatusTree): StatusTree[] {
    return value ? this.clusterEntityService.entityStatusTreeToStatusTree(value) : [];
  }

}
