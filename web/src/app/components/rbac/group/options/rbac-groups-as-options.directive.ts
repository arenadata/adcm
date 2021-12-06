import { Directive, Inject } from '@angular/core';
import { Observable } from 'rxjs';
import { RbacUserModel } from '../../../../models/rbac/rbac-user.model';
import { RbacGroupService } from '../rbac-group.service';

@Directive({
  selector: '[appRbacGroupsAsOptions]',
  exportAs: 'rbacGroups'
})
export class RbacGroupsAsOptionsDirective {
  options$: Observable<RbacUserModel[]>;

  constructor(@Inject(RbacGroupService) public service: RbacGroupService) {
    this.options$ = service.getList();
  }
}
