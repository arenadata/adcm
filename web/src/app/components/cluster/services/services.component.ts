import { Component } from '@angular/core';
import { IColumns } from '@app/adwp';

import { TypeName } from '@app/core/types';
import { ListFactory } from '../../../factories/list.factory';
import { IClusterService } from '@app/models/cluster-service';
import { ConcernListDirective } from '@app/abstract-directives/concern-list.directive';
import { ConcernEventType } from '../../../models/concern/concern-reason';

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
export class ServicesComponent extends ConcernListDirective<IClusterService> {

  type: TypeName = 'service2cluster';
  eventTypes = [ConcernEventType.Service];

  listColumns = [
    ListFactory.nameColumn('display_name'),
    {
      label: 'Version',
      value: (row) => row.version,
    },
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this),
    ListFactory.actionsButton(this),
    ListFactory.importColumn(this),
    ListFactory.configColumn(this),
    ListFactory.maintenanceModeColumn(this, 'service'),
    ListFactory.deleteColumn(this),
  ] as IColumns<IClusterService>;

}
