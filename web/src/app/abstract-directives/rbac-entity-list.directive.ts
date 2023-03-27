import { Directive } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { MatDialog } from '@angular/material/dialog';
import { MatCheckboxChange } from '@angular/material/checkbox';
import { Entity, IListResult, RowEventData, IChoiceColumn } from '@app/adwp';
import * as Immutable from 'immutable';
import { filter } from 'rxjs/operators';
import { zip } from 'rxjs';

import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { DialogComponent } from '@app/shared/components';
import { AdwpListDirective } from './adwp-list.directive';
import { AddButtonComponent, AddButtonDialogConfig } from '../shared/add-component';
import { EntityAbstractService } from '../abstract/entity.abstract.service';

const ADCM_RBAC_ADD_DIALOG_CONFIG: AddButtonDialogConfig = {
  width: '75%',
  maxWidth: '1000px'
};

@Directive({
  selector: '[appRbacEntityList]',
})
export abstract class RbacEntityListDirective<T extends Entity> extends AdwpListDirective<T> {

  abstract getTitle(row: T): string;

  abstract addButton: AddButtonComponent;

  dialogConfig: AddButtonDialogConfig = ADCM_RBAC_ADD_DIALOG_CONFIG;

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected entityService: EntityAbstractService<T>,
  ) {
    super(service, store, route, router, dialog);
  }

  chooseAll(event: MatCheckboxChange): void {
    const { disabled = (row: any) => false } = (this.listColumns.find(({ type }) => type === 'choice') || {}) as IChoiceColumn<any>;
    const value: IListResult<T> = Immutable.fromJS(this.data$.value).toJS() as any;
    value.results.forEach((row: any) => {
      if (!disabled(row)) {
        row.checked = event.checked
      }
    });
    this.data$.next(value);
  }

  deleteEntities(): void {
    const checkedItems = this.data$.value.results.filter((item: any) => item.checked);
    this.dialog
      .open(DialogComponent, {
        data: {
          title: checkedItems.length > 1 ? 'Deleting selected entries' : `Deleting  "${this.getTitle(checkedItems[0])}"`,
          text: 'Are you sure?',
          controls: ['Yes', 'No'],
        },
      })
      .beforeClosed()
      .pipe(filter((yes) => yes))
      .subscribe(() => {
        const rowsToDelete = this.data$.value.results.filter((row: any) => row.checked).map(row => this.entityService.delete(row.id));
        zip(...rowsToDelete).subscribe(() => this.baseListDirective.refresh());
      });
  }

  clickRow(data: RowEventData): void {
    this.showForm(data);
  }

  showForm(data: RowEventData): void {
    const { url } = data.row;
    if (url) {
      this.entityService.getByUrl(data.row.url).pipe(this.takeUntil()).subscribe((entity) => {
        this.addButton.showForm(this.entityService.model(entity));
      });
    }
  }

}
