import { Directive, EventEmitter, Inject, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { filter } from 'rxjs/operators';
import { Store } from '@ngrx/store';
import { ActivatedRoute, Router } from '@angular/router';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatSort, Sort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { MatDialog } from '@angular/material/dialog';
import { BaseDirective, EventHelper } from '@adwp-ui/widgets';

import { EmmitRow, TypeName } from '@app/core/types';
import { BaseListDirective } from '@app/shared/components/list/base-list.directive';
import { SocketState } from '@app/core/store';
import { ListService } from '@app/shared/components/list/list.service';
import { DialogComponent } from '@app/shared/components';
import { StatusData } from '@app/components/columns/status-column/status-column.component';
import { ICluster } from '@app/models/cluster';
import { LIST_SERVICE_PROVIDER } from '@app/shared/components/list/list-service-token';

enum Direction {
  '' = '',
  'asc' = '',
  'desc' = '-',
}

@Directive({
  selector: '[appAbstractList]',
})
export abstract class ListDirective extends BaseDirective implements OnInit, OnDestroy {

  @Input() type: TypeName;

  baseListDirective: BaseListDirective;

  current: any = {};

  @Input()
  columns: Array<string>;

  @Output()
  listItemEvt = new EventEmitter<EmmitRow>();

  paginator: MatPaginator;

  sort: MatSort;

  data: MatTableDataSource<any> = new MatTableDataSource([]);

  @Output() pageEvent = new EventEmitter<PageEvent>();

  addToSorting = false;

  @Input()
  set dataSource(data: { results: any; count: number }) {
    if (data) {
      const list = data.results;
      this.data = new MatTableDataSource<any>(list);
      this.changeCount(data.count);
      if (Array.isArray(list)) {
        this.listItemEvt.emit({ cmd: 'onLoad', row: list[0] });
      }
    }
  }

  sortParam = '';

  constructor(
    @Inject(LIST_SERVICE_PROVIDER) protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
  ) {
    super();
  }

  changeCount(count: number): void {
    this.paginator.length = count;
  }

  clickCell($e: MouseEvent, cmd?: string, row?: any, item?: any): void {
    EventHelper.stopPropagation($e);
    this.current = row;
    this.listItemEvt.emit({ cmd, row, item });
  }

  ngOnInit(): void {
    this.baseListDirective = new BaseListDirective(this, this.service, this.store);
    this.baseListDirective.typeName = this.type;
    this.baseListDirective.init();
  }

  ngOnDestroy(): void {
    this.baseListDirective.destroy();
    super.ngOnDestroy();
  }

  delete($event: MouseEvent, row: any): void {
    EventHelper.stopPropagation($event);
    this.dialog
      .open(DialogComponent, {
        data: {
          title: `Deleting  "${row.name || row.fqdn}"`,
          text: 'Are you sure?',
          controls: ['Yes', 'No'],
        },
      })
      .beforeClosed()
      .pipe(filter((yes) => yes))
      .subscribe(() => this.listItemEvt.emit({ cmd: 'delete', row }));
  }

  maintenanceModeToggle($event: MouseEvent, row: any): void {
    this.listItemEvt.emit({ cmd: 'maintenanceModeToggle', row} )
  }

  getPageIndex(): number {
    return this.paginator.pageIndex;
  }

  getPageSize(): number {
    return this.paginator.pageSize;
  }

  changeSorting(sort: Sort): void {
    const _filter = this.route.snapshot.paramMap.get('filter') || '';
    const pageIndex = this.getPageIndex();
    const pageSize = this.getPageSize();
    const ordering = this.getSortParam(sort);
    const ls = localStorage.getItem('list:param');
    let listParam = ls ? JSON.parse(ls) : null;

    listParam = {
      ...listParam,
      [this.type]: {
        ...listParam?.[this.type],
        ordering
      }
    }

    localStorage.setItem('list:param', JSON.stringify(listParam));

    this.router.navigate(
      [
        './',
        {
          page: pageIndex,
          limit: pageSize,
          filter: _filter,
          ordering,
        },
      ],
      { relativeTo: this.route }
    );

    this.sortParam = ordering;
  }

  getSortParam(a: Sort): string {
    const params: { [key: string]: string[] } = {
      prototype_version: ['prototype_display_name', 'prototype_version'],
    };

    if (a) {
      const dumb = params[a.active] ? params[a.active] : [a.active],
        active = dumb.map((b: string) => `${Direction[a.direction]}${b}`).join(',');

      const current = this.sortParam;
      if (current && this.addToSorting) {
        const result = current
          .split(',')
          .filter((b) => dumb.every((d) => d !== b.replace('-', '')))
          .join(',');
        return [result, a.direction ? active : ''].filter((e) => e).join(',');
      }

      return a.direction ? active : '';
    } else {
      return '';
    }
  }

  getSort(): Sort {
    return this.sort;
  }

  pageHandler(pageEvent: PageEvent): void {
    this.pageEvent.emit(pageEvent);

    const f = this.route.snapshot.paramMap.get('filter') || '';
    const ordering = this.getSortParam(this.getSort());
    const ls = localStorage.getItem('list:param');
    let listParam = ls ? JSON.parse(ls) : null;

    listParam = {
      ...listParam,
      [this.type]: {
        ...listParam?.[this.type],
        limit: String(pageEvent.pageSize),
        page: String(pageEvent.pageIndex),
        filter: f, ordering
      }
    }
    localStorage.setItem('list:param', JSON.stringify(listParam));
    localStorage.setItem('limit', String(pageEvent.pageSize));

    this.router.navigate(['./', listParam?.[this.type]], {
      relativeTo: this.route,
    });
  }

  gotoStatus(data: StatusData<ICluster>): void {
    this.clickCell(data.event, data.action, data.row);
  }

}
