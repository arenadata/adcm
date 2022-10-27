import { Component, forwardRef, OnInit } from '@angular/core';
import { ADD_SERVICE_PROVIDER } from "@app/shared/add-component/add-service-model";
import { RbacAuditOperationsService } from "@app/services/rbac-audit-operations.service";
import { AuditOperationsChangesHistory } from "@app/models/rbac/rbac-audit-operations.model";
import { IColumns } from "@adwp-ui/widgets";
import { ListService } from "@app/shared/components/list/list.service";
import { BehaviorSubject } from "rxjs";

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
      value: (row) => row.old_value,
    },
    {
      label: 'New Value',
      value: (row) => row.new_value,
    }
  ] as IColumns<AuditOperationsChangesHistory>;

  constructor(protected service: ListService,) {}

  ngOnInit(): void {
    const history = Object.keys(this.model.row.object_changes.current).map(v => {
      return {
        attribute: v,
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
