import { Component, ComponentRef, ViewChild } from '@angular/core';
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
      type: 'component',
      headerClassName: 'width30pr',
      className: 'width30pr',
      component: WrapperColumnComponent,
      instanceTaken: (componentRef: ComponentRef<WrapperColumnComponent>) => {
        componentRef.instance.type = ['text-substr'];
        componentRef.instance.customColumnName = 'login_details/username'
      },
    },
    {
      label: 'Result',
      type: 'component',
      headerClassName: 'width30pr',
      className: 'width30pr',
      component: WrapperColumnComponent,
      instanceTaken: (componentRef: ComponentRef<WrapperColumnComponent>) => {
        componentRef.instance.type = ['color'];
        componentRef.instance.customColumnName = 'login_result';
      }
    },
    {
      label: 'Login time',
      sort: 'login_time',
      className: 'width30pr action_date',
      headerClassName: 'width30pr action_date',
      value: (row) => DateHelper.short(row.login_time),
    }
  ] as IColumns<RbacAuditLoginModel>;

  type: TypeName = 'audit_login';
  filteredData$: BehaviorSubject<any> = new BehaviorSubject<any>(null);

  auditLoginFilters: IFilter[] = [
    {
      id: 1, name: 'login', display_name: 'Login', filter_field: 'login_details/username', filter_type: 'input',
    },
    {
      id: 2, name: 'login_result', display_name: 'Result', filter_field: 'login_result', filter_type: 'list',
      options: [
        {id: 1, name: 'account disabled', display_name: 'Account disabled', value: 'account disabled'},
        {id: 2, name: 'success', display_name: 'Success', value: 'success'},
        {id: 3, name: 'user not found', display_name: 'User not found', value: 'user not found'},
        {id: 4, name: 'wrong password', display_name: 'Wrong password', value: 'wrong password'},
      ]
    },
    {
      id: 3, name: 'login_time', display_name: 'Login time', filter_field: 'login_time', filter_type: 'datepicker',
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
    return row.login_details.username;
  }

}
