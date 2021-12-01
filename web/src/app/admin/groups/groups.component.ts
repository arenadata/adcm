import { Component } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';

import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';
import { TypeName } from '../../core/types';

@Component({
  selector: 'app-groups',
  templateUrl: './groups.component.html',
  styleUrls: ['./groups.component.scss']
})
export class GroupsComponent extends AdwpListDirective<RbacGroupModel> {

  listColumns = [
    {
      label: 'Group name',
      sort: 'name',
      value: (row) => row.name,
    },
    {
      label: 'Description',
      sort: 'description',
      value: (row) => row.description,
    },
    {
      label: 'Users',
      value: (row) => row.user.join(', '),
    }
  ] as IColumns<RbacGroupModel>;

  type: TypeName = 'rbac_group';

}
