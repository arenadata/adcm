import { BehaviorSubject } from 'rxjs';
import { Paging } from '@adwp-ui/widgets';
import { Sort } from '@angular/material/sort';
import { ParamMap } from '@angular/router';

import { BaseListDirective } from '@app/shared/components/list/base-list.directive';

export class AdwpBaseListDirective extends BaseListDirective {

  paging: BehaviorSubject<Paging>;
  sorting: BehaviorSubject<Sort> = new BehaviorSubject<Sort>(null);

  routeListener(limit: number, page: number, ordering: string, params: ParamMap) {
    console.log('routeListener');
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
