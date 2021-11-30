import { Component } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';

import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { RbacPolicyModel } from '@app/models/rbac/rbac-policy.model';

@Component({
  selector: 'app-policies',
  templateUrl: './policies.component.html',
  styleUrls: ['./policies.component.scss']
})
export class PoliciesComponent extends AdwpListDirective<RbacPolicyModel> {

  listColumns = [
    {
      label: 'Policy name',
      sort: 'name',
      value: (row) => row.name,
    },
  ] as IColumns<RbacPolicyModel>;

  type: TypeName = 'rbac_policy';

}
