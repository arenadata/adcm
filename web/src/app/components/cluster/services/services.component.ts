import { Component } from '@angular/core';
import { IColumns } from '@adwp-ui/widgets';

import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { ListFactory } from '@app/factories/list-factory';
import { IClusterService } from '@app/models/cluster-service';

@Component({
  selector: 'app-services',
  template: `
    <app-add-button [name]="'service'" class="add-button">Add services</app-add-button>

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
export class ServicesComponent extends AdwpListDirective<IClusterService> {

  type: TypeName = 'service2cluster';

  listColumns = [
    ListFactory.nameColumn('display_name'),
    {
      label: 'Version',
      value: (row) => row.version,
    },
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this),
    ListFactory.actionsColumn(),
    ListFactory.importColumn(this),
    ListFactory.configColumn(this),
  ] as IColumns<IClusterService>;

}
