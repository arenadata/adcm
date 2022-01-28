import { Pipe, PipeTransform } from '@angular/core';
import { RbacRoleModel, RbacRoleParametrizedBy } from '../../../../../models/rbac/rbac-role.model';

@Pipe({
  name: 'parametrizedBy'
})
export class ParametrizedPipe implements PipeTransform {

  transform(role: RbacRoleModel, ...cases: (RbacRoleParametrizedBy | RbacRoleParametrizedBy[])[]): boolean {
    return cases.some((c) => {
      if (Array.isArray(c)) {
        return c.every((value) => role.parametrized_by_type.includes(value));
      }

      return role.parametrized_by_type.length === 1 && role.parametrized_by_type[0] === c;

    });
  }

}
