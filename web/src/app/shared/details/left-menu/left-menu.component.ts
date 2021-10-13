import { AfterViewInit, Component, ComponentFactoryResolver, Input, ViewChild, ViewContainerRef } from '@angular/core';

export interface LeftMenuItem {
  link: string;
  label: string;
  component: any;
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

  constructor(
    protected componentFactoryResolver: ComponentFactoryResolver,
  ) {}

  ngAfterViewInit() {
    setTimeout(() => {
      this.leftMenu.forEach((item) => {
        const componentFactory =
          this.componentFactoryResolver.resolveComponentFactory(item.component);
        const componentRef = this.menuRef.createComponent(componentFactory);
        (componentRef.instance as any).label = item.label;
        (componentRef.instance as any).link = item.link;
      });
    });
  }

}
