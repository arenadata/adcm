import {
  Component,
  EventEmitter,
  Inject,
  Input,
  Output,
  ViewChild,
} from '@angular/core';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { Sort } from '@angular/material/sort';
import { MatCheckboxChange } from '@angular/material/checkbox';

import { BaseDirective } from '../../models/base.directive';
import { ListConfig } from '../list-config';
import { ListConfigService } from '../list-config.service';
import { AdwpRowComponentType, ChoiceEventData, IColumns, InstanceTakenFunc } from '../../models/list';
import { TableComponent } from '../table/table.component';

export interface Paging {
  pageIndex: number;
  pageSize: number;
}

@Component({
  selector: 'adwp-list',
  templateUrl: './list.component.html',
  styleUrls: ['./list.component.scss'],
})
export class ListComponent<T> extends BaseDirective {

  @ViewChild(TableComponent, { static: false }) table: TableComponent<T>;

  @Input() columns: IColumns<T>;
  @Input() dataSource: { results: T[]; count: number; };
  @Input() paging: Paging;
  @Input() sort: Sort;
  @Input() defaultSort: Sort;
  @Input() currentId: number;
  @Input() isRowInactiveHandler: (args: any) => boolean;

  @Input() expandedRow: AdwpRowComponentType<T>;
  @Input() expandedRowClassName: string;
  @Input() expandedRowInstanceTaken: InstanceTakenFunc<T>;

  @Output() clickRow = new EventEmitter<{row: any, event: MouseEvent}>();
  @Output() auxclickRow = new EventEmitter<{row: any, event: MouseEvent}>();
  @Output() changePaging = new EventEmitter<Paging>();
  @Output() changeSort = new EventEmitter<Sort>();

  @Output() choose = new EventEmitter<ChoiceEventData<T>>();
  @Output() chooseAll = new EventEmitter<MatCheckboxChange>();

  @ViewChild(MatPaginator, { static: true }) paginator: MatPaginator;

  constructor(
    @Inject(ListConfigService) public config: ListConfig,
  ) {
    super();
  }

  sortChange(a: Sort): void {
    this.changeSort.emit(a);
  }

  pageHandler(pe: PageEvent): void {
    this.changePaging.emit({ pageIndex: pe.pageIndex + 1, pageSize: pe.pageSize });
  }

}
