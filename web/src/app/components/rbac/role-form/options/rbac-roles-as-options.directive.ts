import { Directive, Inject, Input } from '@angular/core';
import { AdwpHandler, AdwpStringHandler } from '@app/adwp';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';
import { Params } from '@angular/router';
import { RbacOptionsDirective } from '../../../../abstract-directives/rbac-options.directive';
import { RbacRoleService } from '../../../../services/rbac-role.service';

@Directive({
  selector: '[appRbacRolesAsOptions], [rbac-roles-as-options]',
  exportAs: 'rbacRoles'
})
export class RbacRolesAsOptionsDirective extends RbacOptionsDirective {
  initialParams: Params = {
    ordering: 'name'
  };

  @Input('rbac-roles-as-options')
  params: Params;

  id: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => String(item.id);

  label: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => item.display_name;

  category: AdwpHandler<RbacRoleModel, string[]> = (item: RbacRoleModel) => item.category;

  constructor(@Inject(RbacRoleService) public service: RbacRoleService) {
    super(service);
  }
}
