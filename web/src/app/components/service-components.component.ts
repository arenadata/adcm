import { IColumns } from '@adwp-ui/widgets';
import { Component, OnInit } from '@angular/core';
import { Store } from '@ngrx/store';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';

import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { ApiService } from '@app/core/api';
import { TypeName } from '@app/core/types';
import { ListFactory } from '@app/factories/list-factory';

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
export class ServiceComponentsComponent extends AdwpListDirective<any> implements OnInit {

  type: TypeName = 'servicecomponent';

  listColumns = [
    ListFactory.nameColumn('display_name'),
    ListFactory.stateColumn(),
    ListFactory.statusColumn(this),
    ListFactory.actionsButton('servicecomponent'),
    ListFactory.configColumn(this),
  ] as IColumns<any>;

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected api: ApiService,
  ) {
    super(service, store, route, router, dialog, api);
  }

  ngOnInit() {
    super.ngOnInit();
  }

}
