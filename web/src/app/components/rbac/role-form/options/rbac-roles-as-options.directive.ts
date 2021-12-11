import { Directive, Inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AdwpStringHandler } from '@adwp-ui/widgets';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';
import { RbacRoleService } from '../../../../services/rbac-role.service';
import { AdwpHandler } from '../../../../../../../../adwp_ui/projects/widgets/src/lib/cdk';

@Directive({
  selector: '[appRbacRolesAsOptions]',
  exportAs: 'rbacRoles'
})
export class RbacRolesAsOptionsDirective {
  options$: Observable<RbacRoleModel[]>;

  id: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => String(item.id);

  label: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => item.name;

  category: AdwpHandler<RbacRoleModel, string[]> = (item: RbacRoleModel) => item.category;

  constructor(@Inject(RbacRoleService) public service: RbacRoleService) {
    this.options$ = service.getList({ type: 'business' });
  }
}
