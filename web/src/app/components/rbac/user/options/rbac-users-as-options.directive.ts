import { Directive, Inject } from '@angular/core';
import { RbacUserService } from '../rbac-user.service';
import { Observable } from 'rxjs';
import { RbacUserModel } from '../../../../models/rbac/rbac-user.model';

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
