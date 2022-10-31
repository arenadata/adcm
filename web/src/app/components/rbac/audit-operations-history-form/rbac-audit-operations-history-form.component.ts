import { Component, ComponentRef, forwardRef, OnInit } from '@angular/core';
import { ADD_SERVICE_PROVIDER } from "@app/shared/add-component/add-service-model";
import { RbacAuditOperationsService } from "@app/services/rbac-audit-operations.service";
import { AuditOperationsChangesHistory } from "@app/models/rbac/rbac-audit-operations.model";
import { IColumns } from "@adwp-ui/widgets";
import { ListService } from "@app/shared/components/list/list.service";
import { BehaviorSubject } from "rxjs";
import { WrapperColumnComponent } from "@app/components/columns/wrapper-column/wrapper-column.component";

@Component({
  selector: 'app-rbac-audit-operations-form',
  templateUrl: './rbac-audit-operations-history-form.component.html',
  styleUrls: ['./rbac-audit-operations-history-form.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacAuditOperationsService) }
  ]
})
export class RbacAuditOperationsHistoryFormComponent implements OnInit {

  data$: BehaviorSubject<any> = new BehaviorSubject<any>(null);
  model: any;
  listColumns = [
    {
      label: 'Attribute',
      headerClassName: 'width100',
      className: 'width100',
      value: (row) => row.attribute,
    },
    {
      label: 'Old value',
      type: 'component',
      component: WrapperColumnComponent,
      instanceTaken: (componentRef: ComponentRef<WrapperColumnComponent>) => {
        componentRef.instance.type = ['text-substr'];
      }
    },
    {
      label: 'New Value',
      type: 'component',
      component: WrapperColumnComponent,
      instanceTaken: (componentRef: ComponentRef<WrapperColumnComponent>) => {
        componentRef.instance.type = ['text-substr'];
      }
    }
  ] as IColumns<AuditOperationsChangesHistory>;

  constructor(protected service: ListService,) {}

  ngOnInit(): void {
    const history = Object.keys(this.model.row.object_changes.current).map(v => {
      return {
        attribute: (v.charAt(0).toUpperCase() + v.slice(1)).replace('_', ' '),
        new_value: this.model.row.object_changes.current[v],
        old_value: this.model.row.object_changes.previous[v]
      }
    });
    this.data$.next({
      "count": 1,
      "next": null,
      "previous": null,
      "results": history
    });
  }

}
