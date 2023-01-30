import {
  ChangeDetectionStrategy,
  Component,
  ComponentFactory,
  ComponentRef,
  ElementRef,
  EmbeddedViewRef,
  Inject,
  Injector,
  TemplateRef,
  ViewChild,
  ViewContainerRef,
} from '@angular/core';
import { AdwpPortalService } from './portal.service';
import { AdwpPortalHost } from '../../interfaces/portal-host';

const BLANK_CLIENT_RECT: ClientRect = {
  bottom: 0,
  height: 0,
  left: 0,
  right: 0,
  top: 0,
  width: 0,
};


@Component({
  selector: 'adwp-portal-host',
  templateUrl: './portal-host.template.html',
  styleUrls: ['./portal-host.style.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdwpPortalHostComponent implements AdwpPortalHost {
  @ViewChild('positionFixedOffset')
  private readonly positionFixedOffsetRef?: ElementRef<HTMLDivElement>;

  constructor(
    @Inject(ViewContainerRef)
    private readonly viewContainerRef: ViewContainerRef,
    @Inject(ElementRef)
    private readonly elementRef: ElementRef<HTMLElement>,
    @Inject(AdwpPortalService) portalService: AdwpPortalService,
  ) {
    portalService.attach(this);
  }

  get clientRect(): ClientRect {
    return this.elementRef.nativeElement.getBoundingClientRect();
  }

  addComponentChild<C>(
    componentFactory: ComponentFactory<C>,
    injector: Injector,
  ): ComponentRef<C> {
    return this.viewContainerRef.createComponent<C>(
      componentFactory,
      undefined,
      Injector.create({
        parent: injector,
        providers: [
          {
            provide: AdwpPortalHostComponent,
            useValue: this,
          },
        ],
      }),
    );
  }

  addTemplateChild<C>(templateRef: TemplateRef<C>, context?: C): EmbeddedViewRef<C> {
    return this.viewContainerRef.createEmbeddedView(templateRef, context);
  }

  fixedPositionOffset(): ClientRect {
    return this.positionFixedOffsetRef
      ? this.positionFixedOffsetRef.nativeElement.getBoundingClientRect()
      : BLANK_CLIENT_RECT;
  }
}
