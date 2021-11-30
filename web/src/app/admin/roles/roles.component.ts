import { Component } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';

import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { RbacRoleModel } from '@app/models/rbac/rbac-role.model';

@Component({
  selector: 'app-roles',
  templateUrl: './roles.component.html',
  styleUrls: ['./roles.component.scss']
})
export class RolesComponent extends AdwpListDirective<RbacRoleModel> {

  listColumns = [
    {
      label: 'Role name',
      sort: 'name',
      value: (row) => row.name,
    },
    {
      label: 'Description',
      sort: 'description',
      value: (row) => row.description,
    },
  ] as IColumns<RbacRoleModel>;

  type: TypeName = 'rbac_role';

}
