import { AnimationOptions } from '@angular/animations';
import {
  AfterViewChecked,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostBinding,
  Inject,
  NgZone,
  ViewChild,
} from '@angular/core';
import { ANIMATION_FRAME, WINDOW } from '@ng-web-apis/common';
import { fromEvent, merge, Observable } from 'rxjs';
import { takeUntil, throttleTime } from 'rxjs/operators';
import { AdwpDestroyService } from '../../../cdk/services/destroy.service';
import { AdwpAnimationOptions } from '../../interfaces';
import { adwpDropdownAnimation } from '../../animations/animations';
import { AdwpDropdownAnimation } from '../../enums';
import { AdwpDropdown } from '../../interfaces/dropdown-directive';
import { ADWP_ANIMATION_OPTIONS, ADWP_DROPDOWN_DIRECTIVE } from '../../tokens';
import {
  AdwpPortalHostComponent,
  adwpPure,
  adwpZonefree,
  getClosestElement,
  getScreenWidth,
  inRange,
  POLLING_TIME,
  px
} from '../../../cdk';
import { AdwpHorizontalDirection, AdwpVerticalDirection } from '../../types';
import { DEFAULT_MARGIN, DEFAULT_MAX_WIDTH } from '../../constants';
import { getClosestFocusable, setNativeFocused } from '../../../cdk/utils/focus';


@Component({
  selector: 'adwp-dropdown-box',
  templateUrl: './dropdown-box.template.html',
  styleUrls: ['./dropdown-box.style.scss'],
  changeDetection: ChangeDetectionStrategy.Default,
  providers: [AdwpDestroyService],
  animations: [adwpDropdownAnimation],
  host: {
    'class': 'mat-select-panel'
  }
})
export class AdwpDropdownBoxComponent implements AfterViewChecked {
  @HostBinding('@adwpDropdownAnimation')
  dropdownAnimation!: AdwpAnimationOptions;

  private readonly animationTop = {
    value: AdwpDropdownAnimation.FadeInTop,
    ...this.options,
  };

  private readonly animationBottom = {
    value: AdwpDropdownAnimation.FadeInBottom,
    ...this.options,
  };

  private prevDirectionIsTop = false;

  @ViewChild('content', { read: ElementRef })
  readonly contentElementRef?: ElementRef<HTMLElement>;

  constructor(
    @Inject(AdwpDestroyService) destroy$: AdwpDestroyService,
    @Inject(NgZone) ngZone: NgZone,
    @Inject(ADWP_DROPDOWN_DIRECTIVE) readonly directive: AdwpDropdown,
    @Inject(WINDOW) private readonly windowRef: any,
    @Inject(ElementRef) private readonly elementRef: ElementRef<HTMLElement>,
    @Inject(AdwpPortalHostComponent)
    private readonly portalHost: AdwpPortalHostComponent,
    @Inject(ADWP_ANIMATION_OPTIONS) private readonly options: AnimationOptions,
    @Inject(ANIMATION_FRAME) animationFrame$: Observable<number>,
  ) {
    merge(
      animationFrame$.pipe(throttleTime(POLLING_TIME)),
      this.directive.refresh$,
      fromEvent(this.windowRef, 'resize'),
    )
      .pipe(adwpZonefree(ngZone), takeUntil(destroy$))
      .subscribe(() => {
        this.calculatePositionAndSize();
      });
  }

  @adwpPure
  getContext<T extends object>(context?: T): T {
    return context;
  }

  ngAfterViewChecked() {
    this.calculatePositionAndSize();
  }

  onTopFocus() {
    this.moveFocusOutside(true);
  }

  onBottomFocus() {
    this.moveFocusOutside(false);
  }

  @adwpPure
  private get inModal(): boolean {
    return !!getClosestElement(this.directive.host, 'adwp-dialog-host');
  }

  private calculatePositionAndSize() {
    const { clientRect } = this.directive;
    const { style } = this.elementRef.nativeElement;
    const hostRect = this.directive.fixed
      ? this.portalHost.fixedPositionOffset()
      : this.portalHost.clientRect;

    style.position = this.directive.fixed ? 'fixed' : 'absolute';

    this.calculateVerticalPosition(style, clientRect, hostRect);
    this.calculateHorizontalPosition(style, clientRect, hostRect);
    this.calculateWidth(style, clientRect);
  }

  private getFinalAlign(
    style: CSSStyleDeclaration,
    directiveRect: ClientRect,
  ): AdwpHorizontalDirection {
    const dropdownRect = this.elementRef.nativeElement.getBoundingClientRect();
    const dropdownWidth = this.elementRef.nativeElement.offsetWidth;
    const screenWidth = getScreenWidth(this.windowRef.document);
    const isDropdownSizeHypotheticallyFitsViewport =
      directiveRect.left + dropdownWidth < screenWidth ||
      directiveRect.right - dropdownWidth > 0;
    const isDropdownSizeActuallyFitsViewport =
      dropdownRect.right <= screenWidth && dropdownRect.left >= 0;
    let finalAlign: AdwpHorizontalDirection = this.directive.align;

    switch (this.directive.align) {
      case 'left':
        if (
          isDropdownSizeHypotheticallyFitsViewport &&
          dropdownRect.right > screenWidth
        ) {
          finalAlign = 'right';
        }

        break;
      case 'right':
        if (isDropdownSizeHypotheticallyFitsViewport && dropdownRect.left < 0) {
          finalAlign = 'left';
        }

        break;
    }

    if (style.right === 'auto' && isDropdownSizeActuallyFitsViewport) {
      finalAlign = 'left';
    }

    if (style.left === 'auto' && isDropdownSizeActuallyFitsViewport) {
      finalAlign = 'right';
    }

    return finalAlign;
  }

  /**
   * Calculates horizontal position
   *
   * @param style dropdownBox elementRef styles object
   * @param directiveRect ClientRect of hosting directive
   * @param hostRect ClientRect of  portal host
   */
  private calculateHorizontalPosition(
    style: CSSStyleDeclaration,
    directiveRect: ClientRect,
    hostRect: ClientRect,
  ) {
    const offset = this.directive.sided
      ? this.elementRef.nativeElement.getBoundingClientRect().width + DEFAULT_MARGIN
      : 0;
    const left = Math.ceil(directiveRect.left - hostRect.left - offset);
    const right = Math.floor(hostRect.right - directiveRect.right - offset);

    switch (this.getFinalAlign(style, directiveRect)) {
      case 'left':
        if (
          right + DEFAULT_MARGIN > this.windowRef.innerWidth ||
          inRange(left + DEFAULT_MARGIN, 0, this.windowRef.innerWidth)
        ) {
          style.left = px(left);
          style.right = 'auto';
        } else {
          style.left = 'auto';
          style.right = px(right);
        }

        break;
      case 'right':
        if (
          inRange(right + DEFAULT_MARGIN, 0, this.windowRef.innerWidth) ||
          left + DEFAULT_MARGIN > this.windowRef.innerWidth
        ) {
          style.left = 'auto';
          style.right = px(right);
        } else {
          style.left = px(left);
          style.right = 'auto';
        }

        break;
    }
  }

  /**
   * Calculates vertical position and height
   *
   * @param style dropdownBox elementRef styles object
   * @param directiveRect ClientRect of hosting directive
   * @param hostRect ClientRect of  portal host
   */
  private calculateVerticalPosition(
    style: CSSStyleDeclaration,
    directiveRect: ClientRect,
    hostRect: ClientRect,
  ) {
    const windowHeight = this.windowRef.innerHeight;
    // Maximum height of the box
    const boxHeightLimit = Math.min(
      this.directive.maxHeight,
      windowHeight - DEFAULT_MARGIN * 2,
    );
    const offset = this.directive.sided
      ? DEFAULT_MARGIN - directiveRect.height
      : DEFAULT_MARGIN * 2;
    const topAvailableHeight = directiveRect.top - offset;
    const bottomAvailableHeight = windowHeight - directiveRect.bottom - offset;
    const finalDirection = this.getFinalDirection(directiveRect);

    this.prevDirectionIsTop = finalDirection === 'top';

    if (finalDirection === 'top') {
      this.dropdownAnimation = this.animationBottom;

      style.maxHeight = px(Math.min(boxHeightLimit, topAvailableHeight));
      style.top = 'auto';
      style.bottom = px(
        hostRect.bottom - directiveRect.top - DEFAULT_MARGIN + offset,
      );
    } else {
      this.dropdownAnimation = this.animationTop;

      style.maxHeight = px(Math.min(boxHeightLimit, bottomAvailableHeight));
      style.top = px(directiveRect.bottom - hostRect.top - DEFAULT_MARGIN + offset);
      style.bottom = 'auto';
    }
  }

  private getFinalDirection(directiveRect: ClientRect): AdwpVerticalDirection | null {
    const windowHeight = this.windowRef.innerHeight;
    const offset = this.directive.sided
      ? DEFAULT_MARGIN - directiveRect.height
      : DEFAULT_MARGIN * 2;

    // Maximum space available on top and on the bottom in the viewport
    const topAvailableHeight = directiveRect.top - offset;
    const bottomAvailableHeight = windowHeight - directiveRect.bottom - offset;

    let finalDirection: AdwpVerticalDirection | null = null;

    // Given direction is applied if we can fit the box in the limits that way
    switch (this.directive.direction) {
      case 'top':
        if (topAvailableHeight >= this.directive.minHeight) {
          finalDirection = 'top';
        }

        break;
      case 'bottom':
        if (bottomAvailableHeight >= this.directive.minHeight) {
          finalDirection = 'bottom';
        }

        break;
    }

    // Maximum height of the box
    const boxHeightLimit = Math.min(
      this.directive.maxHeight,
      windowHeight - DEFAULT_MARGIN * 2,
    );

    // Choose direction if given direction did not fit
    if (finalDirection === null && this.contentElementRef) {
      // Box height if it fits without scroll
      const visualHeight = Math.min(
        this.contentElementRef.nativeElement.getBoundingClientRect().height +
        (this.elementRef.nativeElement.offsetHeight -
          this.elementRef.nativeElement.clientHeight),
        boxHeightLimit,
      );

      // If there is enough space to fit below without scroll,
      // choose 'bottom', unless it was previously on the top
      if (this.prevDirectionIsTop && topAvailableHeight >= visualHeight) {
        finalDirection = 'top';
      } else if (bottomAvailableHeight >= visualHeight) {
        finalDirection = 'bottom';
      } else {
        // Corner case — select direction with more space
        finalDirection =
          bottomAvailableHeight >= topAvailableHeight ? 'bottom' : 'top';
      }
    }

    return finalDirection;
  }

  /**
   * Calculates width
   *
   * @param style dropdownBox elementRef styles object
   * @param directiveRect ClientRect of hosting directive
   */
  private calculateWidth(style: CSSStyleDeclaration, directiveRect: ClientRect) {
    style.width =
      this.directive.limitMinWidth === 'fixed' && !this.directive.sided
        ? px(directiveRect.width)
        : '';

    if (this.directive.limitMinWidth === 'min' && !this.directive.sided) {
      style.minWidth = px(directiveRect.width);
      style.maxWidth = px(DEFAULT_MAX_WIDTH);

      return;
    }

    style.minWidth = '';
    style.maxWidth = '';
  }

  private moveFocusOutside(previous: boolean) {
    const { host } = this.directive;
    const { ownerDocument } = host;
    const root = ownerDocument ? ownerDocument.body : host;

    let focusable = getClosestFocusable(host, previous, root);

    while (focusable !== null && host.contains(focusable)) {
      focusable = getClosestFocusable(focusable, previous, root);
    }

    if (focusable === null) {
      return;
    }

    setNativeFocused(focusable);
  }
}
