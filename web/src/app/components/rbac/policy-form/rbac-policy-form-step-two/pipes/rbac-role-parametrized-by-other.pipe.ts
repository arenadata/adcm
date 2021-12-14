import { Pipe, PipeTransform } from '@angular/core';
import { RbacRoleModel } from '../../../../../models/rbac/rbac-role.model';

@Pipe({
  name: 'parametrizedByOther'
})
export class RbacRoleParametrizedByOtherPipe implements PipeTransform {

  transform(role: RbacRoleModel): boolean {
    return !role.parametrized_by_type?.includes('service') && !role.parametrized_by_type?.includes('cluster');
  }

}
