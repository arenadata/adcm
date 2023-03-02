import { Component, Input, OnInit } from '@angular/core';

import { ComponentHolderDirective } from '../component-holder.directive';
import { InstanceTakenFunc } from '../../models/list';

@Component({
  selector: 'adwp-component-row',
  template: ``,
})
export class ComponentRowComponent<T> extends ComponentHolderDirective<T> implements OnInit {

  @Input() instanceTaken?: InstanceTakenFunc<T>;

  setData(): void {
    if (this.componentRef) {
      this.componentRef.instance.row = this.row;

      if (this.instanceTaken) {
        this.instanceTaken(this.componentRef);
      }
    }
  }

}
