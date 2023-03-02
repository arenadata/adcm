import {
  AfterViewChecked,
  ComponentFactoryResolver,
  ComponentRef,
  Directive,
  ElementRef,
  Injector,
  Input,
  OnDestroy,
} from '@angular/core';

import { PolymorpheusContent } from '@tinkoff/ng-polymorpheus';
import { Observable } from 'rxjs';
import { AdwpDropdown } from '../interfaces/dropdown-directive';
import { adwpDefaultProp, adwpPure } from '../../cdk';
import { DEFAULT_MAX_HEIGHT, DEFAULT_MIN_HEIGHT } from '../constants';
import { AdwpDropdownWidthT, AdwpHorizontalDirection, AdwpVerticalDirection } from '../types';
import { AdwpDropdownBoxComponent } from '../components/dropdown-box/dropdown-box.component';
import { checkFixedPosition } from '../utils';
import { AdwpPortalService } from '../../cdk/components/portal-host/portal.service';

@Directive()
export abstract class AbstractAdwpDropdown
  implements AdwpDropdown, AfterViewChecked, OnDestroy {
  @Input('adwpDropdownContent')
  @adwpDefaultProp()
  content: PolymorpheusContent = '';

  @Input('adwpDropdownHost')
  @adwpDefaultProp()
  adwpDropdownHost: HTMLElement | null = null;

  @Input('adwpDropdownMinHeight')
  @adwpDefaultProp()
  minHeight = DEFAULT_MIN_HEIGHT;

  @Input('adwpDropdownMaxHeight')
  @adwpDefaultProp()
  maxHeight = DEFAULT_MAX_HEIGHT;

  @Input('adwpDropdownAlign')
  @adwpDefaultProp()
  align: AdwpHorizontalDirection = 'left';

  @Input('adwpDropdownDirection')
  @adwpDefaultProp()
  direction: AdwpVerticalDirection | null = null;

  @Input('adwpDropdownSided')
  @adwpDefaultProp()
  sided = false;

  @Input('adwpDropdownLimitWidth')
  @adwpDefaultProp()
  limitMinWidth: AdwpDropdownWidthT = 'min';

  dropdownBoxRef: ComponentRef<AdwpDropdownBoxComponent> | null = null;

  abstract refresh$: Observable<unknown>;

  protected constructor(
    private readonly componentFactoryResolver: ComponentFactoryResolver,
    private readonly injector: Injector,
    private readonly portalService: AdwpPortalService,
    protected readonly elementRef: ElementRef<HTMLElement>,
  ) {}

  ngOnDestroy() {
    this.closeDropdownBox();
  }

  ngAfterViewChecked() {
    if (this.dropdownBoxRef !== null) {
      this.dropdownBoxRef.changeDetectorRef.detectChanges();
      this.dropdownBoxRef.changeDetectorRef.markForCheck();
    }
  }

  get clientRect(): ClientRect {
    return this.elementRef.nativeElement.getBoundingClientRect();
  }

  get host(): HTMLElement {
    return this.adwpDropdownHost || this.elementRef.nativeElement;
  }

  @adwpPure
  get fixed(): boolean {
    return checkFixedPosition(this.elementRef.nativeElement);
  }

  protected openDropdownBox() {
    if (this.dropdownBoxRef !== null) {
      return;
    }

    const componentFactory = this.componentFactoryResolver.resolveComponentFactory(
      AdwpDropdownBoxComponent,
    );

    this.dropdownBoxRef = this.portalService.add(componentFactory, this.injector);
    this.dropdownBoxRef.changeDetectorRef.detectChanges();
  }

  protected closeDropdownBox() {
    if (this.dropdownBoxRef === null) {
      return;
    }

    this.portalService.remove(this.dropdownBoxRef);
    this.dropdownBoxRef = null;
  }
}
