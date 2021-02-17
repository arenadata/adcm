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
import { Component, ElementRef, Input, OnDestroy, OnInit, QueryList, ViewChild, ViewChildren } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort, MatSortHeader, Sort } from '@angular/material/sort';
import { ActivatedRoute, Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { EventHelper } from '@adwp-ui/widgets';

import { ListDirective } from '@app/abstract-directives/list.directive';
import { ListService } from '@app/shared/components/list/list.service';
import { Store } from '@ngrx/store';
import { SocketState } from '@app/core/store';
import set = Reflect.set;

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
export class ListComponent extends ListDirective implements OnInit, OnDestroy {
  EventHelper = EventHelper;

  selection = new SelectionModel(true, []);

  clustersSubj = new BehaviorSubject<{ id: number; title: string }[]>([]);
  clusters$ = this.clustersSubj.asObservable();

  @Input()
  currentItemId: string;

  @ViewChildren(MatSortHeader, { read: ElementRef }) matSortHeader: QueryList<ElementRef>;

  sorting: MatSort[];

  @ViewChild(MatPaginator, { static: true })
  paginator: MatPaginator;

  @ViewChild(MatSort, { static: true })
  sort: MatSort;

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public dialog: MatDialog,
    public route: ActivatedRoute,
    public router: Router,
  ) {
    super(service, store, route, router, dialog);
  }

  ngOnInit(): void {
    this.sort.sortChange.subscribe((sort: Sort) => this.changeSorting(sort));

    super.ngOnInit();
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

}
