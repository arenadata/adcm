import { Component } from '@angular/core';
import { IColumns, RowEventData } from '@adwp-ui/widgets';
import { AdwpListDirective } from '../../abstract-directives/adwp-list.directive';
import { IHost } from '../../models/host';
import { TypeName } from '../../core/types';
import { ListFactory } from '../../factories/list-factory';


@Component({
  selector: 'app-config-group-host',
  template: `
    <app-add-button [name]="type" class="add-button">Add hosts</app-add-button>

    <adwp-list
      [columns]="listColumns"
      [dataSource]="data$ | async"
      [paging]="paging | async"
      [sort]="sorting | async"
      [defaultSort]="defaultSort"
      (clickRow)="clickRow($event)"
      (auxclickRow)="auxclickRow($event)"
      (changePaging)="onChangePaging($event)"
      (changeSort)="onChangeSort($event)"
    ></adwp-list>
  `,
  styles: [':host { flex: 1; }', '.add-button {position:fixed; right: 20px;top:120px;}'],
})
export class ConfigGroupHostComponent extends AdwpListDirective<IHost> {

  type: TypeName = 'host2configgroup';

  clickRow(data: RowEventData): void {
    console.log('clickRow');
  }

  listColumns = [
    ListFactory.fqdnColumn(),
    {
      type: 'buttons',
      className: 'list-control',
      headerClassName: 'list-control',
      buttons: [{
        icon: 'delete',
        tooltip: 'Remove from config group',
        callback: (row, event) => this.delete(event, row),
      }],
    }
  ] as IColumns<IHost>;

}
