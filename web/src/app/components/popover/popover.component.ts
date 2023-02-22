import {
  Component,
  ViewChild,
  ViewContainerRef,
  ComponentRef,
  Input,
  ComponentFactory,
  ComponentFactoryResolver,
  AfterViewInit,
  Type,
  HostListener, ElementRef, HostBinding,
} from '@angular/core';
import { EventHelper } from '@app/adwp';

import { PopoverContentDirective, PopoverEventFunc } from '@app/abstract-directives/popover-content.directive';
import { PopoverInput } from '@app/directives/popover.directive';

@Component({
  selector: 'app-popover',
  template: `
    <div class="container">
        <ng-container #container></ng-container>
    </div>
  `,
  styleUrls: ['./popover.component.scss']
})
export class PopoverComponent implements AfterViewInit {

  @ViewChild('container', { read: ViewContainerRef }) container: ViewContainerRef;
  containerRef: ComponentRef<PopoverContentDirective>;

  @Input() component: Type<PopoverContentDirective>;
  @Input() data: PopoverInput = {};
  @Input() event: PopoverEventFunc;

  @HostListener('click', ['$event']) click(event: MouseEvent) {
    EventHelper.stopPropagation(event);
  }

  @HostBinding('style.right') right: string;

  constructor(
    private componentFactoryResolver: ComponentFactoryResolver,
    private elementRef: ElementRef,
  ) {}

  ngAfterViewInit() {
    setTimeout(() => {
      const factory: ComponentFactory<any> = this.componentFactoryResolver.resolveComponentFactory(this.component);
      this.container.clear();
      this.containerRef = this.container.createComponent(factory);
      this.containerRef.instance.data = this.data;
      this.containerRef.instance.event = this.event;
      setTimeout(() => {
        const left = document.documentElement.clientWidth - (this.elementRef.nativeElement.offsetLeft + this.elementRef.nativeElement.offsetWidth);
        if (left < 0) {
          this.right = `0px`;
        }
      });
    });
  }

}
