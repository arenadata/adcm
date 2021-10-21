import { AfterViewInit, Component, ComponentFactoryResolver, ComponentRef, Input, Type, ViewChild, ViewContainerRef } from '@angular/core';

import { AdcmEntity } from '@app/models/entity';
import { MenuItemAbstractDirective } from '@app/abstract-directives/menu-item.abstract.directive';

export interface LeftMenuItem {
  link: string;
  label: string;
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
export class LeftMenuComponent implements AfterViewInit {

  @ViewChild('menu', { read: ViewContainerRef }) menuRef: ViewContainerRef;

  @Input() leftMenu: LeftMenuItem[] = [];
  @Input() set entity(entity: AdcmEntity) {
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

  ngAfterViewInit() {
    setTimeout(() => {
      this.leftMenu.forEach((item) => {
        const componentFactory =
          this.componentFactoryResolver.resolveComponentFactory(item.component);
        const componentRef = this.menuRef.createComponent(componentFactory);
        componentRef.instance.label = item.label;
        componentRef.instance.link = item.link;
        if (this.entity !== undefined) {
          componentRef.instance.entity = this.entity;
        }
        this.componentsRef.push(componentRef);
      });
    });
  }

}
