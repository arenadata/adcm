import { Directive, Inject, Input } from '@angular/core';
import { AdwpHandler, AdwpStringHandler } from '@adwp-ui/widgets';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';
import { Params } from '@angular/router';
import { RbacOptionsDirective } from '../../../../abstract-directives/rbac-options.directive';
import { RbacRoleService } from '../../../../services/rbac-role.service';

const RBAC_ROLES_INITIAL_PARAMS: Params = {
  type: 'business'
};

@Directive({
  selector: '[appRbacRolesAsOptions], [rbac-roles-as-options]',
  exportAs: 'rbacRoles'
})
export class RbacRolesAsOptionsDirective extends RbacOptionsDirective {
  initialParams: Params = RBAC_ROLES_INITIAL_PARAMS;

  @Input('rbac-roles-as-options')
  params: Params;

  id: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => String(item.id);

  label: AdwpStringHandler<RbacRoleModel> = (item: RbacRoleModel) => item.name;

  category: AdwpHandler<RbacRoleModel, string[]> = (item: RbacRoleModel) => item.category;

  constructor(@Inject(RbacRoleService) public service: RbacRoleService) {
    super(service);
  }
}
