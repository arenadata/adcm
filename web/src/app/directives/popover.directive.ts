import { ComponentFactory, ComponentFactoryResolver, ComponentRef, Directive, ElementRef, HostListener, Input, OnDestroy, OnInit, Renderer2, Type, ViewContainerRef, } from '@angular/core';
import { BaseDirective } from '@app/adwp';

import { PopoverComponent } from '@app/components/popover/popover.component';
import { PopoverContentDirective, PopoverEventFunc } from '@app/abstract-directives/popover-content.directive';

export interface PopoverInput { [inputKey: string]: any; }

@Directive({
  selector: '[appPopover]'
})
export class PopoverDirective extends BaseDirective implements OnInit, OnDestroy {

  containerRef: ComponentRef<PopoverComponent>;
  factory: ComponentFactory<PopoverComponent>;
  leaveListener: () => void;

  shown = false;
  timeoutId: any;

  @Input() component: Type<PopoverContentDirective>;
  @Input() data: PopoverInput = {};
  @Input() event: PopoverEventFunc;
  @Input() hideTimeout = 0;

  constructor(
    private elementRef: ElementRef,
    public viewContainer: ViewContainerRef,
    public componentFactoryResolver: ComponentFactoryResolver,
    public renderer: Renderer2,
  ) {
    super();
  }

  ngOnInit() {
    this.factory = this.componentFactoryResolver.resolveComponentFactory(PopoverComponent);
  }

  hideComponent() {
    if (!this.timeoutId) {
      this.timeoutId = setTimeout(() => {
        this.clear();
        this.shown = false;
        this.timeoutId = undefined;
      }, this.hideTimeout);
    }
  }

  checkReEnter() {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = undefined;
    }
  }

  @HostListener('mouseenter') mouseEnter() {
    this.checkReEnter();
    if (this.component && !this.shown) {
      this.containerRef = this.viewContainer.createComponent(this.factory);
      this.containerRef.instance.component = this.component;
      this.containerRef.instance.data = this.data;
      this.containerRef.instance.event = this.event;

      this.leaveListener = this.renderer.listen(
        this.elementRef.nativeElement.parentElement,
        'mouseleave',
        () => this.hideComponent(),
      );

      this.renderer.listen(
        this.containerRef.location.nativeElement,
        'mouseenter',
        () => this.checkReEnter(),
      );

      this.shown = true;
    }
  }

  clear() {
    if (this.containerRef) {
      this.containerRef.destroy();
    }

    this.viewContainer.clear();

    if (this.leaveListener) {
      this.elementRef.nativeElement.parentElement.removeEventListener('mouseleave', this.leaveListener);
    }
  }

  ngOnDestroy() {
    super.ngOnDestroy();
    this.clear();
  }

}
