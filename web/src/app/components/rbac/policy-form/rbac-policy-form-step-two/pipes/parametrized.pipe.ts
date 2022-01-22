import { Pipe, PipeTransform } from '@angular/core';
import { RbacRoleModel, RbacRoleParametrizedBy } from '../../../../../models/rbac/rbac-role.model';

@Pipe({
  name: 'parametrizedBy'
})
export class ParametrizedPipe implements PipeTransform {

  transform(role: RbacRoleModel, ...cases: RbacRoleParametrizedBy[][]): boolean {
    return cases.some((c) => c.every((value) => role.parametrized_by_type.includes(value)));
  }

}
