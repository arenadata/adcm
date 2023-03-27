import { ComponentFactory, ComponentRef, EmbeddedViewRef, Injector, TemplateRef } from '@angular/core';

export interface AdwpPortalHost {
  clientRect: ClientRect;

  addComponentChild<C>(componentFactory: ComponentFactory<C>, injector: Injector): ComponentRef<C>;

  addTemplateChild<C>(templateRef: TemplateRef<C>, context?: C): EmbeddedViewRef<C>;

  fixedPositionOffset(): ClientRect;
}
