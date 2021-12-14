import { Pipe, PipeTransform } from '@angular/core';
import { RbacRoleModel } from '../../../../../models/rbac/rbac-role.model';

@Pipe({
  name: 'parametrizedByCluster'
})
export class RbacRoleParametrizedByClusterPipe implements PipeTransform {

  transform(role: RbacRoleModel): boolean {
    return role.parametrized_by_type?.includes('cluster');
  }

}
