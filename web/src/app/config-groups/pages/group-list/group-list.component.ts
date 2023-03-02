import { Component, OnInit, Type } from '@angular/core';
import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { IColumns } from '@app/adwp';
import { ListFactory } from '@app/factories/list.factory';
import { ConfigGroupAddService, ConfigGroupListService } from '../../service';
import { LIST_SERVICE_PROVIDER } from '@app/shared/components/list/list-service-token';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { BaseFormDirective } from '@app/shared/add-component';
import { AddConfigGroupComponent } from '../../components';

@Component({
  selector: 'app-config-group-list',
  template: `
    <app-add-button [name]="type" [component]="addComponent" class="add-button">Add config group</app-add-button>

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
  providers: [
    { provide: LIST_SERVICE_PROVIDER, useClass: ConfigGroupListService },
    { provide: ADD_SERVICE_PROVIDER, useClass: ConfigGroupAddService }
  ],
})
export class ConfigGroupListComponent extends AdwpListDirective<any> implements OnInit {
  type: TypeName = 'group_config';
  addComponent: Type<BaseFormDirective> = AddConfigGroupComponent;

  listColumns: IColumns<any> = [
    ListFactory.nameColumn(),
    ListFactory.descriptionColumn(),
    ListFactory.deleteColumn(this),
  ];
}
