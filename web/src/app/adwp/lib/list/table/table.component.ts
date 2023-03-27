import { Component, Input, Output, EventEmitter, ViewChild } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import { MatSort, Sort } from '@angular/material/sort';
import { MatCheckboxChange } from '@angular/material/checkbox';

import { AdwpRowComponentType, ButtonCallback, ChoiceEventData, IColumn, IColumns, InstanceTakenFunc } from '../../models/list';
import { GUID } from '../../helpers/guid';
import { Entity } from '../../models/entity';
import { EventHelper } from '../../helpers/event-helper';
import { BaseDirective } from '../../models/base.directive';
import { RowEventData } from '../../models/list';

@Component({
  selector: 'adwp-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent<T> extends BaseDirective {

  @ViewChild(MatSort, { static: false }) sort: MatSort;

  headerRow: string[];

  ownColumns: IColumns<T>;
  @Input() set columns(columns: IColumns<T>) {
    this.headerRow = [];
    columns.forEach((column) => {
      const guid = GUID.generate();
      this.headerRow.push(guid);
      column.guid = guid;
    });
    this.ownColumns = columns;
  }

  ownExpandedRow: AdwpRowComponentType<T>;
  @Input() set expandedRow(expandedRow: AdwpRowComponentType<T>) {
    this.ownExpandedRow = expandedRow;
  }

  get expandedRow(): AdwpRowComponentType<T> {
    return this.ownExpandedRow;
  }

  @Input() expandedRowClassName: string;

  @Input() expandedRowInstanceTaken: InstanceTakenFunc<T>;

  data: MatTableDataSource<any> = new MatTableDataSource([]);

  @Input() set dataSource(data: { results: any; count: number }) {
    if (data) {
      const list = data.results;
      this.data = new MatTableDataSource<any>(list);
    }
  }

  @Input() rowStatusChecker: (args: any) => boolean;

  @Input() order: Sort;
  @Input() defaultOrder: Sort;

  @Input() currentId: number;

  @Input() headerRowClassName: string;

  @Output() clickRow = new EventEmitter<RowEventData>();
  @Output() auxclickRow = new EventEmitter<RowEventData>();
  @Output() sortChange = new EventEmitter<Sort>();

  @Output() choose = new EventEmitter<ChoiceEventData<T>>();
  @Output() chooseAll = new EventEmitter<MatCheckboxChange>();

  changeSort(sort: Sort): void {
    if (sort.direction) {
      this.sortChange.emit(sort);
    } else {
      this.sortChange.emit(this.defaultOrder);
    }
  }

  invokeCallback(callback: ButtonCallback<any>, row: any, event: MouseEvent): void {
    EventHelper.stopPropagation(event);
    callback(row, event);
  }

  onClickRow(row: T, event: MouseEvent): void {
    EventHelper.stopPropagation(event);
    this.clickRow.emit({ row, event});
  }

  onAuxclickRow(row: T, event: MouseEvent): void {
    EventHelper.stopPropagation(event);
    this.auxclickRow.emit({ row, event });
  }

  trackBy(index: number, item: Entity): number {
    return item.id;
  }

  onChoose(event: ChoiceEventData<T>): void {
    this.choose.emit(event);
  }

  onChooseAll(event: MatCheckboxChange): void {
    const mainCheckbox = event.source;

    // steps: indeterminate -> unchecked -> checked
    // if click when indeterminate need send false state to parent handlers
    // for switch off all checkboxes
    if (mainCheckbox.indeterminate) {
      event.checked = false;
    }
    // in real mainCheckbox.checked must calc from IsAllCheckedPipe
    // but some times mat-checkbox set inner checked value after click
    // and not correct recalc after change items checkboxes
    //
    // bug case without manual `mainCheckbox.checked = false`:
    // 1. check main checkbox,
    // 2. uncheck all items checkboxes
    // 3. after uncheck last item - main checkbox will be view as checked(!)
    mainCheckbox.checked = false;

    this.chooseAll.emit(event);
  }

  clickCheckbox(event: any): void {
    event.stopPropagation();
  }

  clickOnCell(data: { event: any, column: IColumn<any> }): void {
    if (data.column.type === 'choice') {
      data.event.stopPropagation();
    }
  }

}
