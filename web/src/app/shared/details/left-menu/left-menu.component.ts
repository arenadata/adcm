import { Component, ComponentFactoryResolver, ComponentRef, Input, Type, ViewChild, ViewContainerRef } from '@angular/core';

import { AdcmEntity } from '@app/models/entity';
import { MenuItemAbstractDirective } from '@app/abstract-directives/menu-item.abstract.directive';

export interface LeftMenuItem {
  link: string;
  label: string;
  data?: any;
  component: Type<MenuItemAbstractDirective>;
}

@Component({
  selector: 'app-left-menu',
  template: `
    <mat-nav-list>
      <ng-container #menu></ng-container>
    </mat-nav-list>
  `,
  styleUrls: ['./left-menu.component.scss']
})
export class LeftMenuComponent {

  @ViewChild('menu', { read: ViewContainerRef }) menuRef: ViewContainerRef;

  private _leftMenu: LeftMenuItem[] = [];
  @Input() set leftMenu(leftMenu: LeftMenuItem[]) {
    this._leftMenu = leftMenu;
    this.rebuildComponents();
  }
  get leftMenu(): LeftMenuItem[] {
    return this._leftMenu;
  }

  @Input() set entity(entity: AdcmEntity) {
    this._entity = entity;
    this.componentsRef.forEach((componentRef) => componentRef.instance.entity = entity);
  }
  get entity(): AdcmEntity {
    return this._entity;
  }

  private componentsRef: Array<ComponentRef<any>> = [];
  private _entity: AdcmEntity;

  constructor(
    protected componentFactoryResolver: ComponentFactoryResolver,
  ) {}

  rebuildComponents() {
    setTimeout(() => {
      this.componentsRef = [];
      this.menuRef.clear();
      this.leftMenu.forEach((item) => {
        const componentFactory =
          this.componentFactoryResolver.resolveComponentFactory(item.component);
        const componentRef = this.menuRef.createComponent(componentFactory);
        componentRef.instance.label = item.label;
        componentRef.instance.link = item.link;
        if (item.data) {
          componentRef.instance.data = item.data;
        }
        if (this.entity !== undefined) {
          componentRef.instance.entity = this.entity;
        }
        this.componentsRef.push(componentRef);
      });
    });
  }

}
