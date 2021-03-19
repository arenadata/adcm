import {
  Component,
  ViewChild,
  ViewContainerRef,
  ComponentRef,
  Input,
  ComponentFactory,
  ComponentFactoryResolver, AfterViewInit, Type, HostListener,
} from '@angular/core';
import { PopoverContentDirective } from '@app/abstract-directives/popover-content.directive';
import { PopoverInput } from '@app/directives/popover.directive';
import { EventHelper } from '@adwp-ui/widgets';

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

  @HostListener('click', ['$event']) click(event: MouseEvent) {
    EventHelper.stopPropagation(event);
  }

  constructor(
    private componentFactoryResolver: ComponentFactoryResolver,
  ) {}

  ngAfterViewInit() {
    setTimeout(() => {
      const factory: ComponentFactory<any> = this.componentFactoryResolver.resolveComponentFactory(this.component);
      this.container.clear();
      this.containerRef = this.container.createComponent(factory);
      this.containerRef.instance.data = this.data;
    });
  }

}
