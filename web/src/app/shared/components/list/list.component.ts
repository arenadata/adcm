// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { SelectionModel } from '@angular/cdk/collections';
import { Component, ElementRef, EventEmitter, Input, OnInit, Output, QueryList, ViewChild, ViewChildren } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatSort, MatSortHeader, Sort } from '@angular/material/sort';
import { MatTableDataSource } from '@angular/material/table';
import { ActivatedRoute, Router } from '@angular/router';
import { EmmitRow, isIssue, Issue, TypeName } from '@app/core/types';
import { BehaviorSubject } from 'rxjs';
import { filter } from 'rxjs/operators';

import { DialogComponent } from '../dialog.component';

enum Direction {
  '' = '',
  'asc' = '',
  'desc' = '-',
}

export interface ListResult<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

@Component({
  selector: 'app-list',
  templateUrl: './list.component.html',
  styleUrls: ['./list.component.scss'],
})
export class ListComponent implements OnInit {
  selection = new SelectionModel(true, []);
  current: any = {};
  type: TypeName;

  clustersSubj = new BehaviorSubject<{ id: number; title: string }[]>([]);
  clusters$ = this.clustersSubj.asObservable();

  @Input()
  currentItemId: string;
  @Input()
  columns: Array<string>;

  data: MatTableDataSource<any> = new MatTableDataSource([]);
  @Input()
  set dataSource(data: { results: any; count: number }) {
    if (data) {
      const list = data.results;
      this.data = new MatTableDataSource<any>(list);
      this.paginator.length = data.count;
      this.listItemEvt.emit({ cmd: 'onLoad', row: list[0] });
    }
  }

  @Output()
  listItemEvt = new EventEmitter<EmmitRow>();

  @Output() pageEvent = new EventEmitter<PageEvent>();

  @ViewChild(MatPaginator, { static: true })
  paginator: MatPaginator;

  @ViewChild(MatSort, { static: true })
  sort: MatSort;

  @ViewChildren(MatSortHeader, { read: ElementRef }) matSortHeader: QueryList<ElementRef>;

  addToSorting = false;
  sorting: MatSort[];
  sortParam = '';

  constructor(public dialog: MatDialog, public router: Router, public route: ActivatedRoute) {}

  getSortParam(a: Sort) {
    const penis: { [key: string]: string[] } = {
      prototype_version: ['prototype_display_name', 'prototype_version'],
    };

    const dumb = penis[a.active] ? penis[a.active] : [a.active],
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
  }

  ngOnInit(): void {
    this.sort.sortChange.subscribe((a: Sort) => {
      const _filter = this.route.snapshot.paramMap.get('filter') || '',
        { pageIndex, pageSize } = this.paginator,
        ordering = this.getSortParam(a);

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
    });
  }

  pageHandler(pageEvent: PageEvent) {
    this.pageEvent.emit(pageEvent);
    localStorage.setItem('limit', String(pageEvent.pageSize));
    const f = this.route.snapshot.paramMap.get('filter') || '';
    const ordering = this.getSortParam(this.sort);
    this.router.navigate(['./', { page: pageEvent.pageIndex, limit: pageEvent.pageSize, filter: f, ordering }], {
      relativeTo: this.route,
    });
  }

  trackBy(item: any) {
    return item.id || item;
  }

  /** Whether the number of selected elements matches the total number of rows. */
  isAllSelected() {
    const numSelected = this.selection.selected.length;
    const numRows = this.data.data.length;
    return numSelected === numRows;
  }

  /** Selects all rows if they are not all selected; otherwise clear selection. */
  masterToggle() {
    this.isAllSelected() ? this.selection.clear() : this.data.data.forEach((row) => this.selection.select(row));
  }

  getClusterData(row: any) {
    const { id, hostcomponent } = row.cluster || row;
    const { action } = row;
    return { id, hostcomponent, action };
  }

  stopPropagation($e: MouseEvent) {
    $e.stopPropagation();
    return $e;
  }

  notIssue(issue: Issue): boolean {
    return !isIssue(issue);
  }

  clickCell($e: MouseEvent, cmd: string, row: any, item?: any) {
    if ($e && $e.stopPropagation) $e.stopPropagation();
    this.current = row;
    this.listItemEvt.emit({ cmd, row, item });
  }

  delete($event: MouseEvent, row: any) {
    $event.stopPropagation();
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
}
