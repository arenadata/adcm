import { Component } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Store } from '@ngrx/store';

import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';
import { TypeName } from '@app/core/types';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { RbacGroupService } from '@app/services/rbac-group.service';
import { RbacEntityListDirective } from '@app/abstract-directives/rbac-entity-list.directive';

@Component({
  selector: 'app-groups',
  templateUrl: './groups.component.html',
  styleUrls: ['./groups.component.scss']
})
export class GroupsComponent extends RbacEntityListDirective<RbacGroupModel> {

  listColumns = [
    {
      type: 'choice',
      modelKey: 'checked',
      className: 'choice-column',
      headerClassName: 'choice-column',
    },
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

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected entityService: RbacGroupService,
  ) {
    super(service, store, route, router, dialog, entityService);
  }

  getTitle(row: RbacGroupModel): string {
    return row.name;
  }

}
