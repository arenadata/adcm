import { Component } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Store } from '@ngrx/store';

import { TypeName } from '@app/core/types';
import { RbacPolicyModel } from '@app/models/rbac/rbac-policy.model';
import { RbacRoleModel } from '@app/models/rbac/rbac-role.model';
import { RbacEntityListDirective } from '@app/abstract-directives/rbac-entity-list.directive';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { RbacPolicyService } from '@app/services/rbac-policy.service';

@Component({
  selector: 'app-policies',
  templateUrl: './policies.component.html',
  styleUrls: ['./policies.component.scss']
})
export class PoliciesComponent extends RbacEntityListDirective<RbacPolicyModel> {

  listColumns = [
    {
      type: 'choice',
      modelKey: 'checked',
      className: 'choice-column',
      headerClassName: 'choice-column',
    },
    {
      label: 'Policy name',
      sort: 'name',
      value: (row) => row.name,
    },
  ] as IColumns<RbacPolicyModel>;

  type: TypeName = 'rbac_policy';

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected entityService: RbacPolicyService,
  ) {
    super(service, store, route, router, dialog, entityService);
  }

  getTitle(row: RbacRoleModel): string {
    return row.name;
  }

}
