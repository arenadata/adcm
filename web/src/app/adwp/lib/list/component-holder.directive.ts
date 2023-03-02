import { ComponentFactoryResolver, ComponentRef, Directive, Input, OnInit, ViewContainerRef } from '@angular/core';

import { BaseDirective } from '../models/base.directive';
import { AdwpComponentHolder } from '../models/list';

@Directive()
export abstract class ComponentHolderDirective<T> extends BaseDirective implements OnInit {

  @Input() component: AdwpComponentHolder<T>;

  private ownRow: T;
  @Input() set row(row: T) {
    this.ownRow = row;
    this.setData();
  }
  get row(): T {
    return this.ownRow;
  }

  componentRef: ComponentRef<AdwpComponentHolder<T>>;

  constructor(
    protected componentFactoryResolver: ComponentFactoryResolver,
    protected viewContainerRef: ViewContainerRef,
  ) {
    super();
  }

  abstract setData(): void;

  ngOnInit(): void {
    const componentFactory =
      this.componentFactoryResolver.resolveComponentFactory(this.component as any);
    this.viewContainerRef.clear();
    this.componentRef = this.viewContainerRef.createComponent(componentFactory) as any;
    this.setData();
  }

}
