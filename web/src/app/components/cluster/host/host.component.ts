import { Component } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';

import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { TypeName } from '@app/core/types';
import { IHost } from '@app/models/host';
import { ListFactory } from '@app/factories/list-factory';

@Component({
  selector: 'app-cluster-host',
  template: `
    <app-add-button [name]="type" class="add-button">Add hosts</app-add-button>
    <app-list class="main" [type]="type"></app-list>

    <br>
    <br>

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
export class HostComponent extends AdwpListDirective<IHost> {

  type: TypeName = 'host2cluster';

  listColumns = [
    ListFactory.fqdnColumn(),
    ListFactory.providerColumn(),
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this.takeUntil.bind(this), this.gotoStatus.bind(this)),
    ListFactory.actionsColumn(),
    ListFactory.configColumn(this),
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
