import { Component, ComponentRef, Input, OnInit } from '@angular/core';

import { AdwpCellComponent, IComponentColumn } from '../../models/list';
import { ComponentHolderDirective } from '../component-holder.directive';

@Component({
  selector: 'adwp-component-cell',
  template: ``,
})
export class ComponentCellComponent<T> extends ComponentHolderDirective<T> implements OnInit {

  @Input() component: AdwpCellComponent<T>;

  private ownColumn: IComponentColumn<T>;
  @Input() set column(column: IComponentColumn<T>) {
    this.ownColumn = column;
    this.setData();
  }
  get column(): IComponentColumn<T> {
    return this.ownColumn;
  }

  componentRef: ComponentRef<AdwpCellComponent<T>>;

  setData(): void {
    if (this.componentRef) {
      this.componentRef.instance.row = this.row;
      this.componentRef.instance.column = this.column;

      if (this.column && this.column.instanceTaken) {
        this.column.instanceTaken(this.componentRef);
      }
    }
  }

}
