import { Directive, Inject } from '@angular/core';
import { Observable } from 'rxjs';
import { RbacGroupService } from '../../../../services/rbac-group.service';
import { RbacGroupModel } from '../../../../models/rbac/rbac-group.model';

@Directive({
  selector: '[appRbacGroupsAsOptions]',
  exportAs: 'rbacGroups'
})
export class RbacGroupsAsOptionsDirective {
  options$: Observable<RbacGroupModel[]>;

  constructor(@Inject(RbacGroupService) public service: RbacGroupService) {
    this.options$ = service.getList();
  }
}
