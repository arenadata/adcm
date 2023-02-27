import { Component } from '@angular/core';
import { IColumns } from '@app/adwp';

import { TypeName } from '@app/core/types';
import { IHost } from '@app/models/host';
import { ListFactory } from '../../../factories/list.factory';
import { ConcernListDirective } from '@app/abstract-directives/concern-list.directive';
import { ConcernEventType } from '@app/models/concern/concern-reason';

@Component({
  selector: 'app-cluster-host',
  template: `
    <app-add-button [name]="type" class="add-button">Add hosts</app-add-button>

    <adwp-list
      [columns]="listColumns"
      [dataSource]="data$ | async"
      [paging]="paging | async"
      [sort]="sorting | async"
      [defaultSort]="defaultSort"
      [currentId]="current ? current.id : undefined"
      (clickRow)="clickRow($event)"
      (auxclickRow)="auxclickRow($event)"
      (changePaging)="onChangePaging($event)"
      (changeSort)="onChangeSort($event)"
    ></adwp-list>
  `,
  styles: [':host { flex: 1; }', '.add-button {position:fixed; right: 20px;top:120px;}'],
})
export class ClusterHostComponent extends ConcernListDirective<IHost> {

  type: TypeName = 'host2cluster';
  eventTypes = [ConcernEventType.Host];

  listColumns = [
    ListFactory.fqdnColumn(),
    ListFactory.providerColumn(),
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this),
    ListFactory.actionsButton(this),
    ListFactory.configColumn(this),
    ListFactory.maintenanceModeColumn(this, 'host'),
    {
      type: 'buttons',
      className: 'list-control',
      headerClassName: 'list-control',
      buttons: [{
        icon: 'link_off',
        tooltip: 'Remove from cluster',
        callback: (row, event) => this.delete(event, row),
      }],
    }
  ] as IColumns<IHost>;

}
