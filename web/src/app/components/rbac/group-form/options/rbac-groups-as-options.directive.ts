import { Directive, Inject } from '@angular/core';
import { Observable } from 'rxjs';
import { RbacGroupService } from '../../../../services/rbac-group.service';
import { RbacGroupModel } from '../../../../models/rbac/rbac-group.model';
import { AdwpStringHandler } from '@adwp-ui/widgets';

@Directive({
  selector: '[appRbacGroupsAsOptions]',
  exportAs: 'rbacGroups'
})
export class RbacGroupsAsOptionsDirective {
  options$: Observable<RbacGroupModel[]>;

  label: AdwpStringHandler<RbacGroupModel> = (item: RbacGroupModel) => item.name;

  constructor(@Inject(RbacGroupService) public service: RbacGroupService) {
    this.options$ = service.getList();
  }
}
