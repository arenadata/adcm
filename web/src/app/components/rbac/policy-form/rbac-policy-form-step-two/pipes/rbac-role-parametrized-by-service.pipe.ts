import { Pipe, PipeTransform } from '@angular/core';
import { RbacRoleModel } from '../../../../../models/rbac/rbac-role.model';

@Pipe({
  name: 'parametrizedByService'
})
export class RbacRoleParametrizedByServicePipe implements PipeTransform {

  transform(role: RbacRoleModel): boolean {
    return role.parametrized_by_type?.includes('service');
  }

}
