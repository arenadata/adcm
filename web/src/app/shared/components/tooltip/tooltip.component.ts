// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import {
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Injector,
  OnDestroy,
  OnInit,
  Renderer2,
  Type,
} from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { delay } from 'rxjs/operators';

import { IssueInfoComponent } from '../issue-info.component';
import { StatusInfoComponent } from '../status-info.component';
import { ComponentData, TooltipOptions, TooltipService } from './tooltip.service';

@Component({
  selector: 'app-tooltip',
  template: `
    {{ contentAsString }}
    <ng-container *ngComponentOutlet="CurrentComponent; injector: componentInjector"></ng-container>
  `,
  styleUrls: ['./tooltip.component.scss'],
})
export class TooltipComponent implements OnInit, OnDestroy {
  private options: TooltipOptions;
  contentAsString: string;
  to: any;
  ss: Subscription;
  es: Subscription;

  CurrentComponent: Type<IssueInfoComponent | StatusInfoComponent>;
  componentInjector: Injector;

  constructor(
    private el: ElementRef,
    private service: TooltipService,
    private renderer: Renderer2,
    private router: Router,
    private parentInjector: Injector
  ) {}

  @HostListener('mouseenter', ['$event']) menter() {
    clearTimeout(this.to);
  }

  @HostListener('mousedown') mdown() {}

  @HostListener('mouseleave') mleave() {
    this.render().position();
  }

  ngOnInit(): void {
    this.ss = this.service.position$.subscribe(o => {
      clearTimeout(this.to);
      if (!o) this.to = setTimeout(() => this.render().position(), 500);
      else this.render(o);
    });
  }

  ngOnDestroy() {
    this.ss.unsubscribe();
    this.es.unsubscribe();
  }

  render(o?: TooltipOptions) {
    this.options = o;
    this.clear().content();
    if (o)
      this.options.source.onclick = () => {
        this.clear();
        this.renderer.setAttribute(this.el.nativeElement, 'style', `opacity: 0`);
      };
    return this;
  }

  clear() {
    this.contentAsString = '';
    this.CurrentComponent = null;
    return this;
  }

  content() {
    if (!this.options) return;
    if (typeof this.options.content === 'string') {
      this.contentAsString = this.options.content;
      this.position();
    }

    if (typeof this.options.content === 'object') {
      this.buildComponent();
    }
  }

  position() {
    const o = this.options;
    const el = this.el.nativeElement;
    if (o) {
      const bodyWidth = document.querySelector('body').offsetWidth,
        bodyHeight = (document.getElementsByTagName('app-root')[0] as HTMLElement).offsetHeight,
        extRight = o.event.x + el.offsetWidth + o.source.offsetWidth / 2,
        extBottom = o.event.y + el.offsetHeight;

      const dx = bodyWidth < extRight ? o.event.x - (extRight - bodyWidth) : o.event.x + o.source.offsetWidth / 2,
        dy = o.event.y,
        b = bodyHeight < extBottom ? 'bottom: 20px;' : '';
      this.renderer.setAttribute(el, 'style', `left:${dx}px; top:${dy}px; ${b} opacity: .9`);
    } else {
      this.renderer.setAttribute(el, 'style', `opacity: 0`);
    }
  }

  buildComponent() {
    const component = { issue: IssueInfoComponent, status: StatusInfoComponent }[this.options.componentName];
    this.CurrentComponent = component;

    const emitter = new EventEmitter();
    this.es = emitter.pipe(delay(100)).subscribe(() => this.position());

    this.componentInjector = Injector.create({
      providers: [
        {
          provide: ComponentData,
          useValue: { typeName: this.router.url, current: this.options.content, emitter: emitter },
        },
      ],
      parent: this.parentInjector,
    });
  }
}
