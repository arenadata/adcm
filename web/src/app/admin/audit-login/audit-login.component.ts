import { Component, ComponentRef, Type, ViewChild } from '@angular/core';
import { ADD_SERVICE_PROVIDER } from "../../shared/add-component/add-service-model";
import { IColumns } from "@adwp-ui/widgets";
import { TypeName } from "../../core/types";
import { ListService } from "../../shared/components/list/list.service";
import { Store } from "@ngrx/store";
import { SocketState } from "../../core/store";
import { ActivatedRoute, Router } from "@angular/router";
import { MatDialog } from "@angular/material/dialog";
import { RbacEntityListDirective } from "../../abstract-directives/rbac-entity-list.directive";
import { RbacAuditLoginModel } from "../../models/rbac/rbac-audit-login.model";
import { AddButtonComponent } from "../../shared/add-component";
import { RbacAuditLoginService } from "../../services/rbac-audit-login.service";
import { BehaviorSubject } from "rxjs";
import { IFilter } from "../../shared/configuration/tools/filter/filter.component";
import { DateHelper } from "../../helpers/date-helper";
import { WrapperColumnComponent } from "../../components/columns/wrapper-column/wrapper-column.component";

@Component({
  selector: 'app-audit-login',
  templateUrl: './audit-login.component.html',
  styleUrls: ['./audit-login.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: RbacAuditLoginService }
  ],
})
export class AuditLoginComponent extends RbacEntityListDirective<RbacAuditLoginModel> {
  @ViewChild(AddButtonComponent) addButton: AddButtonComponent;

  listColumns = [
    {
      label: 'Login',
      headerClassName: 'width30pr',
      className: 'width30pr',
      value: (row) => row.login,
    },
    {
      label: 'Result',
      type: 'component',
      headerClassName: 'width100',
      className: 'width100',
      component: WrapperColumnComponent,
      instanceTaken: (componentRef: ComponentRef<WrapperColumnComponent>) => {
        componentRef.instance.type = ['color'];
      }
    },
    {
      label: 'Login time',
      sort: 'login_time',
      className: 'action_date',
      headerClassName: 'action_date',
      value: (row) => DateHelper.short(row.login_time),
    }
  ] as IColumns<RbacAuditLoginModel>;

  type: TypeName = 'audit_login';
  filteredData$: BehaviorSubject<any> = new BehaviorSubject<any>(null);

  auditLoginFilters: IFilter[] = [
    {
      id: 1, name: 'username', display_name: 'Username', filter_field: 'username', filter_type: 'input',
    },
    {
      id: 2, name: 'object_name', display_name: 'Object name', filter_field: 'object_name', filter_type: 'input',
    },
    {
      id: 3, name: 'object_type', display_name: 'Object type', filter_field: 'object_type', filter_type: 'list',
      options: [
        {id: 1, name: 'adcm', display_name: 'Adcm', value: 'adcm'},
        {id: 2, name: 'bundle', display_name: 'Bundle', value: 'bundle'},
        {id: 3, name: 'cluster', display_name: 'Cluster', value: 'cluster'},
        {id: 4, name: 'component', display_name: 'Component', value: 'component'},
        {id: 5, name: 'group', display_name: 'Group', value: 'group'},
        {id: 6, name: 'host', display_name: 'Host', value: 'host'},
        {id: 7, name: 'policy', display_name: 'Policy', value: 'policy'},
        {id: 8, name: 'provider', display_name: 'Provider', value: 'provider'},
        {id: 9, name: 'role', display_name: 'Role', value: 'role'},
        {id: 10, name: 'service', display_name: 'Service', value: 'service'},
        {id: 11, name: 'user', display_name: 'User', value: 'user'},
      ]
    },
    {
      id: 4, name: 'operation_type', display_name: 'Operation type', filter_field: 'operation_type', filter_type: 'list',
      options: [
        {id: 1, name: 'create', display_name: 'Create', value: 'create'},
        {id: 2, name: 'update', display_name: 'Update', value: 'update'},
        {id: 3, name: 'delete', display_name: 'Delete', value: 'delete'},
      ]
    },
    {
      id: 5, name: 'operation_result', display_name: 'Operation result', filter_field: 'operation_result', filter_type: 'list',
      options: [
        {id: 1, name: 'success', display_name: 'Success', value: 'success'},
        {id: 2, name: 'fail', display_name: 'Fail', value: 'fail'},
        {id: 3, name: 'denied', display_name: 'Denied', value: 'denied'},
      ]
    },
    {
      id: 6, name: 'operation_time', display_name: 'Operation time', filter_field: 'operation_time', filter_type: 'datepicker',
    },
  ];

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected entityService: RbacAuditLoginService,
  ) {
    super(service, store, route, router, dialog, entityService);
  }

  getTitle(row: RbacAuditLoginModel): string {
    return row.login;
  }

}
