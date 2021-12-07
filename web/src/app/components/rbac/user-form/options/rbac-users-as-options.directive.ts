import { Directive, Inject } from '@angular/core';
import { Observable } from 'rxjs';
import { RbacUserModel } from '../../../../models/rbac/rbac-user.model';
import { RbacUserService } from '../../../../services/rbac-user.service';

@Directive({
  selector: '[appRbacUsersAsOptions]',
  exportAs: 'rbacUsers'
})
export class RbacUsersAsOptionsDirective {
  options$: Observable<RbacUserModel[]>;

  constructor(@Inject(RbacUserService) public service: RbacUserService) {
    this.options$ = service.getList();
  }
}
