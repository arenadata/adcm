import { Directive, Inject, Input } from '@angular/core';
import { RbacUserModel } from '../../../../models/rbac/rbac-user.model';
import { RbacUserService } from '../../../../services/rbac-user.service';
import { AdwpStringHandler } from '@app/adwp';
import { Params } from '@angular/router';
import { RbacOptionsDirective } from '../../../../abstract-directives/rbac-options.directive';

@Directive({
  selector: '[appRbacUsersAsOptions], [rbac-users-as-options]',
  exportAs: 'rbacUsers'
})
export class RbacUsersAsOptionsDirective extends RbacOptionsDirective {
  initialParams: Params = {
    ordering: 'username'
  };

  @Input('rbac-users-as-options')
  params: Params;

  label: AdwpStringHandler<RbacUserModel> = (item: RbacUserModel) => item.username;

  constructor(@Inject(RbacUserService) public service: RbacUserService) {
    super(service);
  }
}
