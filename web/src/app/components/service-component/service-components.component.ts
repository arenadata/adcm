import { IColumns } from '@adwp-ui/widgets';
import { Component } from '@angular/core';

import { TypeName } from '@app/core/types';
import { ListFactory } from '@app/factories/list.factory';
import { ConcernListDirective } from '@app/abstract-directives/concern-list.directive';
import { ConcernEventType } from '@app/models/concern/concern-reason';

@Component({
  selector: 'app-service-components',
  template: `
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
  styles: [`
    :host { flex: 1; }
  `],
})
export class ServiceComponentsComponent extends ConcernListDirective<any> {

  type: TypeName = 'servicecomponent';
  eventTypes = [ConcernEventType.ServiceComponent];

  listColumns = [
    ListFactory.nameColumn('display_name'),
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this),
    ListFactory.actionsButton(this),
    ListFactory.configColumn(this),
    ListFactory.maintenanceModeColumn(this, 'component'),
  ] as IColumns<any>;

}
