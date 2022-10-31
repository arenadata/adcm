import {Component, ComponentRef, Type, ViewChild} from '@angular/core';
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
  RbacAuditOperationsHistoryFormComponent
} from "../../components/rbac/audit-operations-history-form/rbac-audit-operations-history-form.component";
import { BehaviorSubject } from "rxjs";
import { IFilter } from "../../shared/configuration/tools/filter/filter.component";
import { HistoryColumnComponent } from "../../components/columns/history-column/history-column.component";
import { DateHelper } from "../../helpers/date-helper";
import { WrapperColumnComponent } from "../../components/columns/wrapper-column/wrapper-column.component";

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
      type: 'component',
      headerClassName: 'width30pr',
      className: 'width30pr',
      component: WrapperColumnComponent,
      instanceTaken: (componentRef: ComponentRef<WrapperColumnComponent>) => {
        componentRef.instance.type = ['text-substr'];
      }
    },
    {
      label: 'Operation name',
      value: (row) => row.operation_name,
    },
    {
      label: 'Operation type',
      type: 'component',
      headerClassName: 'width100',
      className: 'width100',
      component: WrapperColumnComponent,
      value: (row) => row.operation_type,
      instanceTaken: (componentRef: ComponentRef<WrapperColumnComponent>) => {
        componentRef.instance.type = ['color'];
      }
    },
    {
      label: 'Operation result',
      type: 'component',
      headerClassName: 'width100',
      className: 'width100',
      component: WrapperColumnComponent,
      value: (row) => row.operation_result,
      instanceTaken: (componentRef: ComponentRef<WrapperColumnComponent>) => {
        componentRef.instance.type = ['color'];
      }
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
      id: 1, name: 'username', display_name: 'Username', filter_field: 'username', filter_type: 'input',
    },
    {
      id: 2, name: 'object_name', display_name: 'Object name', filter_field: 'object_name', filter_type: 'input',
    },
    {
      id: 3, name: 'object_type', display_name: 'Object type', filter_field: 'object_type', filter_type: 'list',
      options: [
        {id: 1, name: 'adcm', display_name: 'Adcm', value: 'adcm'},
        {id: 2, name: 'audit_operations', display_name: 'Audit Operations', value: 'audit_operations'},
        {id: 3, name: 'bundle', display_name: 'Bundle', value: 'bundle'},
        {id: 4, name: 'cluster', display_name: 'Cluster', value: 'cluster'},
        {id: 5, name: 'component', display_name: 'Component', value: 'component'},
        {id: 6, name: 'group', display_name: 'Group', value: 'group'},
        {id: 7, name: 'group_config', display_name: 'Group Configuration', value: 'group_config'},
        {id: 8, name: 'group_config_hosts', display_name: 'Host Group Configuration', value: 'group_config_hosts'},
        {id: 9, name: 'host', display_name: 'Host', value: 'host'},
        {id: 10, name: 'host2cluster', display_name: 'Cluster Host', value: 'host2cluster'},
        {id: 11, name: 'hostcomponent', display_name: 'Host Component', value: 'hostcomponent'},
        {id: 12, name: 'job', display_name: 'Job', value: 'job'},
        {id: 13, name: 'policy', display_name: 'policy', value: 'policy'},
        {id: 14, name: 'profile', display_name: 'Profile', value: 'profile'},
        {id: 15, name: 'provider', display_name: 'Provider', value: 'provider'},
        {id: 16, name: 'role', display_name: 'Role', value: 'role'},
        {id: 17, name: 'service', display_name: 'Service', value: 'service'},
        {id: 18, name: 'service2cluster', display_name: 'Cluster Service', value: 'service2cluster'},
        {id: 19, name: 'servicecomponent', display_name: 'Service Component', value: 'servicecomponent'},
        {id: 20, name: 'stats', display_name: 'Stats', value: 'stats'},
        {id: 21, name: 'task', display_name: 'Task', value: 'task'},
        {id: 22, name: 'user', display_name: 'User', value: 'user'},
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
      ]
    },
    {
      id: 6, name: 'operation_time', display_name: 'Operation time', filter_field: 'operation_time', filter_type: 'datepicker',
    },
  ];

  component: Type<RbacAuditOperationsHistoryFormComponent> = RbacAuditOperationsHistoryFormComponent;

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
