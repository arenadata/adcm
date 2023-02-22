import { BehaviorSubject } from 'rxjs';
import { Paging } from '@app/adwp';
import { Sort } from '@angular/material/sort';
import { ParamMap } from '@angular/router';
import { Store } from '@ngrx/store';

import { BaseListDirective } from '@app/shared/components/list/base-list.directive';
import { TypeName } from '@app/core/types';
import { ListDirective } from '@app/abstract-directives/list.directive';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';

export class AdwpBaseListDirective extends BaseListDirective {

  paging: BehaviorSubject<Paging>;
  sorting: BehaviorSubject<Sort> = new BehaviorSubject<Sort>(null);

  constructor(
    protected parent: ListDirective,
    protected service: ListService,
    protected store: Store<SocketState>,
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

}
