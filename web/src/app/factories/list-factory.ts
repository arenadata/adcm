import { IComponentColumn, IValueColumn, IButtonsColumn } from '@adwp-ui/widgets';
import { ComponentRef } from '@angular/core';
import { MonoTypeOperatorFunction } from 'rxjs';

import { StateColumnComponent } from '@app/components/columns/state-column/state-column.component';
import { StatusColumnComponent } from '@app/components/columns/status-column/status-column.component';
import { ActionsColumnComponent } from '@app/components/columns/actions-column/actions-column.component';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { UpgradeComponent } from '@app/shared';

export class ListFactory {

  static nameColumn(): IValueColumn<any> {
    return {
      label: 'Name',
      sort: 'name',
      value: (row) => row.display_name || row.name,
    };
  }

  static stateColumn(): IComponentColumn<any> {
    return {
      label: 'State',
      sort: 'state',
      type: 'component',
      className: 'width100',
      headerClassName: 'width100',
      component: StateColumnComponent,
    };
  }

  static statusColumn<T>(
    takeUntil: () => MonoTypeOperatorFunction<any>,
    onClickCallback: (data: any) => void,
  ): IComponentColumn<T> {
    return {
      label: 'Status',
      sort: 'status',
      type: 'component',
      className: 'list-control',
      headerClassName: 'list-control',
      component: StatusColumnComponent,
      instanceTaken: (componentRef: ComponentRef<StatusColumnComponent<T>>) => {
        componentRef.instance.onClick
          .pipe(takeUntil())
          .subscribe((data) => onClickCallback(data));
      }
    };
  }

  static actionsColumn(): IComponentColumn<any> {
    return {
      label: 'Actions',
      type: 'component',
      className: 'list-control',
      headerClassName: 'list-control',
      component: ActionsColumnComponent,
    };
  }

  static importColumn<T>(listDirective: AdwpListDirective<T>): IButtonsColumn<T> {
    return {
      label: 'Import',
      type: 'buttons',
      className: 'list-control',
      headerClassName: 'list-control',
      buttons: [{
        icon: 'import_export',
        callback: (row) => listDirective.baseListDirective.listEvents({ cmd: 'import', row }),
      }]
    };
  }

  static configColumn<T>(listDirective: AdwpListDirective<T>): IButtonsColumn<T> {
    return {
      label: 'Config',
      type: 'buttons',
      className: 'list-control',
      headerClassName: 'list-control',
      buttons: [{
        icon: 'settings',
        callback: (row) => listDirective.baseListDirective.listEvents({ cmd: 'config', row }),
      }]
    };
  }

  static bundleColumn(): IValueColumn<any> {
    return {
      label: 'Bundle',
      sort: 'prototype_version',
      value: (row) => [row.prototype_display_name || row.prototype_name, row.prototype_version, row.edition].join(' '),
    };
  }

  static updateColumn(): IComponentColumn<any> {
    return {
      label: 'Upgrade',
      type: 'component',
      className: 'list-control',
      headerClassName: 'list-control',
      component: UpgradeComponent,
    };
  }

  static deleteColumn<T>(listDirective: AdwpListDirective<T>): IButtonsColumn<T> {
    return {
      type: 'buttons',
      className: 'list-control',
      headerClassName: 'list-control',
      buttons: [{
        icon: 'delete',
        callback: (row, event) => listDirective.delete(event, row),
      }]
    };
  }

}
