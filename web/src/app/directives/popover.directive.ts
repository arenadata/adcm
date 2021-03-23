import {
  Directive,
  ElementRef,
  HostListener,
  Input,
  ViewContainerRef,
  ComponentFactoryResolver,
  ComponentFactory,
  ComponentRef,
  OnDestroy,
  OnInit,
  Renderer2, Type,
} from '@angular/core';
import { BaseDirective } from '@adwp-ui/widgets';

import { PopoverComponent } from '@app/components/popover/popover.component';
import { PopoverContentDirective } from '@app/abstract-directives/popover-content.directive';

export interface PopoverInput { [inputKey: string]: any; }

@Directive({
  selector: '[appPopover]'
})
export class PopoverDirective extends BaseDirective implements OnInit, OnDestroy {

  containerRef: ComponentRef<PopoverComponent>;
  factory: ComponentFactory<PopoverComponent>;
  leaveListener: () => void;

  @Input() component: Type<PopoverContentDirective>;
  @Input() data: PopoverInput = {};

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

  @HostListener('mouseenter') mouseEnter() {
    if (this.component) {
      this.containerRef = this.viewContainer.createComponent(this.factory);
      this.containerRef.instance.component = this.component;
      this.containerRef.instance.data = this.data;
      this.leaveListener = this.renderer.listen(
        this.elementRef.nativeElement.parentElement,
        'mouseleave',
        () => this.clear(),
      );
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
