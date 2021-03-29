import { BehaviorSubject } from 'rxjs';
import { Paging } from '@adwp-ui/widgets';
import { Sort } from '@angular/material/sort';
import { ParamMap } from '@angular/router';

import { BaseListDirective } from '@app/shared/components/list/base-list.directive';
import { Host as AdcmHost, TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { IHost } from '@app/models/host';
import { ICluster } from '@app/models/cluster';
import { IListResult } from '@adwp-ui/widgets';
import { ListDirective } from '@app/abstract-directives/list.directive';
import { ListService } from '@app/shared/components/list/list.service';
import { Store } from '@ngrx/store';
import { SocketState } from '@app/core/store';
import { ApiService } from '@app/core/api';

export class AdwpBaseListDirective extends BaseListDirective {

  paging: BehaviorSubject<Paging>;
  sorting: BehaviorSubject<Sort> = new BehaviorSubject<Sort>(null);

  constructor(
    protected parent: ListDirective,
    protected service: ListService,
    protected store: Store<SocketState>,
    private api: ApiService,
  ) {
    super(parent, service, store);
  }

  checkType(typeName: string, referenceTypeName: TypeName): boolean {
    if (referenceTypeName === 'servicecomponent') {
      return typeName === 'component';
    }

    return (referenceTypeName ? referenceTypeName.split('2')[0] : referenceTypeName) === typeName;
  }

  routeListener(limit: number, page: number, ordering: string, params: ParamMap) {
    this.paging.next({ pageIndex: page + 1, pageSize: limit });
    if (ordering) {
      const direction = ordering[0] === '-' ? 'desc' : 'asc';
      const active = ordering[0] === '-' ? ordering.substr(1) : ordering;
      this.sorting.next({ direction, active });
    }

    this.listParams = params;
    this.refresh();
  }

  addCluster(id: number) {
    if (id) {
      this.service.addClusterToHost(id, this.row as AdcmHost)
        .subscribe((host) => {
          if ((this.parent as AdwpListDirective<IHost>)?.data$?.value?.results) {
            this.api.getOne('cluster', host.cluster_id).subscribe((cluster: ICluster) => {
              const tableData = Object.assign({}, (this.parent as AdwpListDirective<IHost>).data$.value);
              const index = tableData.results.findIndex(item => item.id === host.id);
              const row = Object.assign({}, tableData.results[index]);

              row.cluster_id = cluster.id;
              row.cluster_name = cluster.name;

              tableData.results.splice(index, 1, row);
              (this.parent as AdwpListDirective<IHost>).reload(tableData as IListResult<any>);
            });
          }
        });
    }
  }

}
