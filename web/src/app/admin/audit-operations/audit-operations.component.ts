import { Component, Type, ViewChild } from '@angular/core';
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
import {
  RbacAuditOperationsFormComponent
} from "../../components/rbac/audit-operations-form/rbac-audit-operations-form.component";
import {BehaviorSubject} from "rxjs";
import {IFilter} from "../../shared/configuration/tools/filter/filter.component";
import {HistoryColumnComponent} from "../../components/columns/history-column/history-column.component";
import {DateHelper} from "../../helpers/date-helper";

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
      headerClassName: 'width100',
      className: 'width100',
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
      headerClassName: 'width100',
      className: 'width100',
      value: (row) => row.operation_type,
    },
    {
      label: 'Operation result',
      headerClassName: 'width100',
      className: 'width100',
      value: (row) => row.operation_result,
    },
    {
      label: 'Operation time',
      sort: 'operation_time',
      className: 'action_date',
      headerClassName: 'action_date',
      value: (row) => DateHelper.short(row.operation_time),
    },
    {
      label: 'Username',
      headerClassName: 'width100',
      className: 'width100',
      value: (row) => row.username,
    },
    {
      label: '',
      type: 'component',
      headerClassName: 'width100',
      className: 'width100',
      component: HistoryColumnComponent,
    }

  ] as IColumns<RbacAuditOperationsModel>;

  type: TypeName = 'audit_operations';
  filteredData$: BehaviorSubject<any> = new BehaviorSubject<any>(null);

  auditOperationsFilters: IFilter[] = [
    {
      id: 1, name: 'status', display_name: 'Status', filter_field: 'is_active',
      options: [
        {id: 1, name: 'active', display_name: 'Active', value: true},
        {id: 2, name: 'inactive', display_name: 'Inactive', value: false},
      ]
    },
  ];

  component: Type<RbacAuditOperationsFormComponent> = RbacAuditOperationsFormComponent;

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
