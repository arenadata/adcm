import { Component, ViewChild } from '@angular/core';
import { ADD_SERVICE_PROVIDER } from "../../shared/add-component/add-service-model";
import { IColumns } from "@adwp-ui/widgets";
import { TypeName } from "../../core/types";
import { ListService } from "../../shared/components/list/list.service";
import { Store } from "@ngrx/store";
import { SocketState } from "../../core/store";
import { ActivatedRoute, Router } from "@angular/router";
import { MatDialog } from "@angular/material/dialog";
import { RbacEntityListDirective } from "../../abstract-directives/rbac-entity-list.directive";
import { RbacAuditOperationsModel } from "../../models/rbac/rbac-audit-operations.model";
import { AddButtonComponent } from "../../shared/add-component";
import { RbacAuditOperationsService } from "../../services/rbac-audit-operations.service";

@Component({
  selector: 'app-audit-operations',
  templateUrl: './audit-operations.component.html',
  styleUrls: ['./audit-operations.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacAuditOperationsService }
  ],
})
export class AuditOperationsComponent extends RbacEntityListDirective<RbacAuditOperationsModel> {
  @ViewChild(AddButtonComponent) addButton: AddButtonComponent;

  listColumns = [
    {
      label: 'Object type',
      value: (row) => row.object_type,
    },
    {
      label: 'Object name',
      value: (row) => row.object_name,
    },
    {
      label: 'Operation name',
      value: (row) => row.operation_name,
    },
    {
      label: 'Operation type',
      value: (row) => row.operation_type,
    },
    {
      label: 'Operation result',
      value: (row) => row.operation_result,
    },
    {
      label: 'Operation time',
      sort: 'operation_time',
      value: (row) => row.operation_time,
    },
    {
      label: 'Username',
      value: (row) => row.username,
    },

  ] as IColumns<RbacAuditOperationsModel>;

  type: TypeName = 'audit_operations';

  // component: Type<RbacPolicyFormComponent> = RbacPolicyFormComponent;

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected entityService: RbacAuditOperationsService,
  ) {
    super(service, store, route, router, dialog, entityService);
  }

  getTitle(row: RbacAuditOperationsModel): string {
    return row.object_name;
  }

}
