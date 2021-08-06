import { Component, OnInit } from '@angular/core';
import { EmmitRow, TypeName } from '../../../core/types';
import { AdwpListDirective } from '../../../abstract-directives/adwp-list.directive';
import { IColumns } from '@adwp-ui/widgets';
import { ListFactory } from '../../../factories/list-factory';
import { ConfigGroupListService } from '../../service/config-group-list.service';
import { LIST_SERVICE_PROVIDER } from '../../../shared/components/list/list-service-token';

@Component({
  selector: 'app-config-group-list',
  template: `
    <!--    <app-add-button [name]="type" class="add-button">Add config group</app-add-button>-->

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
  providers: [{ provide: LIST_SERVICE_PROVIDER, useClass: ConfigGroupListService }],
})
export class ConfigGroupListComponent extends AdwpListDirective<any> implements OnInit {
  type: TypeName = 'configgroup';

  listColumns: IColumns<any> = [
    ListFactory.nameColumn(),
    ListFactory.descriptionColumn(),
    ListFactory.deleteColumn(this),
  ];

  ngOnInit() {
    super.ngOnInit();
    this.baseListDirective.listEvents = this.listEvents;
  }

  listEvents(event: EmmitRow) {
    // this.service.
    console.log(event);
  }


  // deleteGroup(item: ConfigGroup) {
  //   console.log('deleteGroup | item: ', item);
  //
  //   this.service
  //     .delete(item)
  //     .pipe(this.takeUntil())
  //     .subscribe();
  // }
}
