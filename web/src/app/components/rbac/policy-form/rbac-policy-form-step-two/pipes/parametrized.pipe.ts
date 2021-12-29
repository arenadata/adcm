import { Pipe, PipeTransform } from '@angular/core';
import { RbacRoleModel, RbacRoleParametrizedBy } from '../../../../../models/rbac/rbac-role.model';

@Pipe({
  name: 'parametrizedBy'
})
export class ParametrizedPipe implements PipeTransform {

  transform(role: RbacRoleModel, values: RbacRoleParametrizedBy[]): boolean {
    return !!role.parametrized_by_type.filter((item) => values.includes(item)).length;
  }

}
