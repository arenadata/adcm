import { Component } from '@angular/core';
import { TypeName } from '@app/core/types';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { IColumns } from '@adwp-ui/widgets';
import { ListFactory } from '@app/factories/list-factory';

@Component({
  selector: 'app-config-groups',
  template: `
    <app-add-button [name]="type" class="add-button">Add config group</app-add-button>

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
export class ConfigGroupsComponent extends AdwpListDirective<any> {
  type: TypeName = 'config_group';

  listColumns: IColumns<any> = [
    ListFactory.nameColumn(),
    ListFactory.descriptionColumn(),
    ListFactory.deleteColumn(this),
  ];

}
