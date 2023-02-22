import { Component, Type } from '@angular/core';
import { IColumns, RowEventData } from '@app/adwp';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { TypeName } from '@app/core/types';
import { ListFactory } from '@app/factories/list.factory';
import { IHost } from '@app/models/host';
import { LIST_SERVICE_PROVIDER } from '@app/shared/components/list/list-service-token';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { ConfigGroupHostAddService, ConfigGroupHostListService } from '../../service';
import { BaseFormDirective } from '@app/shared/add-component';
import { AddHostToConfigGroupComponent } from '../../components';


@Component({
  selector: 'app-config-group-host-list',
  template: `
    <app-add-button [name]="type" [component]="addComponent" class="add-button">Add hosts</app-add-button>

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
  providers: [
    { provide: LIST_SERVICE_PROVIDER, useClass: ConfigGroupHostListService },
    { provide: ADD_SERVICE_PROVIDER, useClass: ConfigGroupHostAddService }
  ],
})
export class ConfigGroupHostListComponent extends AdwpListDirective<IHost> {
  type: TypeName = 'group_config_hosts';
  addComponent: Type<BaseFormDirective> = AddHostToConfigGroupComponent;

  listColumns = [
    ListFactory.fqdnColumn(),
    ListFactory.deleteColumn(this),
  ] as IColumns<IHost>;

  clickRow(data: RowEventData): void {
    data.event.preventDefault();
    data.event.stopPropagation();
    return;
  }

}
