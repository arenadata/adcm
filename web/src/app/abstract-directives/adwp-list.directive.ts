import { Directive, OnInit } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { IColumns, IListResult, Paging, RowEventData } from '@app/adwp';
import { Sort } from '@angular/material/sort';
import { PageEvent } from '@angular/material/paginator';

import { ListDirective } from './list.directive';
import { AdwpBaseListDirective } from './adwp-base-list.directive';
import { BaseEntity, Entities } from '@app/core/types';

@Directive({
  selector: '[appAdwpList]',
})
export abstract class AdwpListDirective<T> extends ListDirective implements OnInit {

  abstract listColumns: IColumns<T>;

  data$: BehaviorSubject<IListResult<T>> = new BehaviorSubject(null);

  paging: BehaviorSubject<Paging> = new BehaviorSubject<Paging>(null);
  sorting: BehaviorSubject<Sort> = new BehaviorSubject<Sort>(null);

  defaultSort: Sort = { active: 'id', direction: 'desc' };

  reload(data: IListResult<Entities>) {
    this.data$.next(data as any);
  }

  initBaseListDirective() {
    this.baseListDirective = new AdwpBaseListDirective(this, this.service, this.store);
    this.baseListDirective.typeName = this.type;
    this.baseListDirective.reload = this.reload.bind(this);
    (this.baseListDirective as AdwpBaseListDirective).paging = this.paging;
    (this.baseListDirective as AdwpBaseListDirective).sorting = this.sorting;
    this.baseListDirective.init();
  }

  ngOnInit() {
    this.initBaseListDirective();
  }

  clickRow(data: RowEventData) {
    this.clickCell(data.event, 'title', data.row);
  }

  auxclickRow(data: RowEventData) {
    this.clickCell(data.event, 'new-tab', data.row);
  }

  changeCount(count: number) {}

  getPageIndex(): number {
    return this.paging.value.pageIndex - 1;
  }

  getPageSize(): number {
    return this.paging.value.pageSize;
  }

  onChangePaging(paging: Paging): void {
    this.paging.next(paging);

    const pageEvent = new PageEvent();
    pageEvent.pageIndex = this.getPageIndex();
    pageEvent.length = this.data$.value.count;
    pageEvent.pageSize = this.getPageSize();

    this.pageHandler(pageEvent);
  }

  onChangeSort(sort: Sort): void {
    this.sorting.next(sort);
    this.changeSorting(sort);
  }

  getSort(): Sort {
    return this.sorting.value;
  }

  rewriteRow(row: BaseEntity) {
    this.service.checkItem(row).subscribe((item) => Object.keys(row).map((a) => (row[a] = item[a])));
  }

  findRow(id: number): BaseEntity {
    return this.data.data.find((item) => item.id === id);
  }

}
