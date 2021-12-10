import { Directive, Inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AdwpStringHandler } from '@adwp-ui/widgets';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';
import { RbacRoleService } from '../../../../services/rbac-role.service';

@Directive({
  selector: '[appRbacRolesAsOptions]',
  exportAs: 'rbacRoles'
})
export class RbacRolesAsOptionsDirective {
  options$: Observable<RbacRoleModel[]>;

  label: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => item.name;

  constructor(@Inject(RbacRoleService) public service: RbacRoleService) {
    this.options$ = service.getList();
  }
}
