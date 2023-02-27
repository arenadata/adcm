import { ComponentFactory, ComponentRef, EmbeddedViewRef, Injectable, Injector, TemplateRef, } from '@angular/core';
import { AdwpPortalHost } from '../../interfaces/portal-host';

const NO_HOST = 'Portals cannot be used without AdwpPortalHostComponent';

@Injectable({
  providedIn: 'root',
})
export class AdwpPortalService {
  private host?: AdwpPortalHost;

  private get safeHost(): AdwpPortalHost {
    if (!this.host) {
      throw new Error(NO_HOST);
    }

    return this.host;
  }

  attach(host: AdwpPortalHost): void {
    this.host = host;
  }

  add<C>(componentFactory: ComponentFactory<C>, injector: Injector): ComponentRef<C> {
    return this.safeHost.addComponentChild(componentFactory, injector);
  }

  remove<C>({ hostView }: ComponentRef<C>) {
    hostView.destroy();
  }

  addTemplate<C>(templateRef: TemplateRef<C>, context?: C): EmbeddedViewRef<C> {
    return this.safeHost.addTemplateChild(templateRef, context);
  }

  removeTemplate<C>(viewRef: EmbeddedViewRef<C>) {
    viewRef.destroy();
  }
}
