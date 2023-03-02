import {
  AfterViewChecked,
  ComponentFactoryResolver,
  Directive,
  ElementRef,
  forwardRef,
  Inject,
  Injector,
  Input,
  OnDestroy,
} from '@angular/core';

import { ADWP_DROPDOWN_DIRECTIVE } from '../../tokens';
import { AbstractAdwpDropdown } from '../../abstract/abstract-dropdown';
import { AdwpDropdown } from '../../interfaces/dropdown-directive';
import { AdwpParentsScrollService } from '../../../cdk/services';
import { AdwpPortalService } from '../../../cdk/components/portal-host/portal.service';

@Directive({
  selector: '[adwpDropdown]:not(ng-container)',
  providers: [
    {
      provide: ADWP_DROPDOWN_DIRECTIVE,
      useExisting: forwardRef(() => AdwpDropdownDirective),
    },
    AdwpParentsScrollService,
  ],
})
export class AdwpDropdownDirective
  extends AbstractAdwpDropdown
  implements AdwpDropdown, AfterViewChecked, OnDestroy {
  @Input('adwpDropdown')
  set open(value: boolean) {
    if (value) {
      this.openDropdownBox();
    } else {
      this.closeDropdownBox();
    }
  }

  constructor(
    @Inject(ComponentFactoryResolver)
      componentFactoryResolver: ComponentFactoryResolver,
    @Inject(Injector) injector: Injector,
    @Inject(AdwpPortalService)
      portalService: AdwpPortalService,
    @Inject(ElementRef) elementRef: ElementRef<HTMLElement>,
    @Inject(AdwpParentsScrollService) readonly refresh$: AdwpParentsScrollService,
  ) {
    super(componentFactoryResolver, injector, portalService, elementRef);
  }
}
