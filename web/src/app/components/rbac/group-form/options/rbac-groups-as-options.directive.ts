import { Directive, Inject, Input } from '@angular/core';
import { RbacGroupService } from '../../../../services/rbac-group.service';
import { RbacGroupModel } from '../../../../models/rbac/rbac-group.model';
import { AdwpStringHandler } from '@app/adwp';
import { Params } from '@angular/router';
import { RbacOptionsDirective } from '../../../../abstract-directives/rbac-options.directive';

@Directive({
  selector: '[appRbacGroupsAsOptions], [rbac-groups-as-options]',
  exportAs: 'rbacGroups'
})
export class RbacGroupsAsOptionsDirective extends RbacOptionsDirective {
  initialParams: Params = {
    ordering: 'name'
  };

  @Input('rbac-groups-as-options')
  params: Params;

  label: AdwpStringHandler<RbacGroupModel> = (item: RbacGroupModel) => item.name;

  constructor(@Inject(RbacGroupService) public service: RbacGroupService) {
    super(service);
  }
}
