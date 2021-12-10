import { Directive, Inject } from '@angular/core';
import { Observable } from 'rxjs';
import { RbacUserModel } from '../../../../models/rbac/rbac-user.model';
import { RbacUserService } from '../../../../services/rbac-user.service';
import { AdwpStringHandler } from '@adwp-ui/widgets';

@Directive({
  selector: '[appRbacUsersAsOptions]',
  exportAs: 'rbacUsers'
})
export class RbacUsersAsOptionsDirective {
  options$: Observable<RbacUserModel[]>;

  label: AdwpStringHandler<RbacUserModel> = (item: RbacUserModel) => item.username;

  constructor(@Inject(RbacUserService) public service: RbacUserService) {
    this.options$ = service.getList();
  }
}
