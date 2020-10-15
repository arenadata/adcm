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
import { Directive, ElementRef, EventEmitter, HostListener, Input, Output, Renderer2 } from '@angular/core';

@Directive({
  selector: '[appMultiSort]',
})
export class MultiSortDirective {
  shiftKey = false;
  private params: string[] = [];

  @Input('appMultiSort') set sortParam(param: string) {
    const el = this.el.nativeElement;
    this.params = param.split(',');
    this.hideAllArrows(el);
    setTimeout(() => this.params.map((p) => this.preCell(p, el)), 0);
  }

  @Output() mousedownevent = new EventEmitter<boolean>();

  @HostListener('mousedown', ['$event']) onmousedown(e: MouseEvent) {
    this.shiftKey = e.shiftKey;
    this.mousedownevent.emit(e.shiftKey);
  }

  @HostListener('mouseover', ['$event.target']) onmouseover(h: HTMLElement) {
    const el = this.el.nativeElement;
    this.params.map((p) => this.preCell(p, el));
  }

  @HostListener('mouseout', ['$event.target']) mouseleave(row: HTMLElement) {
    const el = this.el.nativeElement;
    setTimeout(() => this.params.map((p) => this.preCell(p, el)), 300);
  }

  constructor(private el: ElementRef, private renderer: Renderer2) {}

  hideAllArrows(el: any) {
    Array.from<HTMLElement>(el.getElementsByTagName('mat-header-cell')).forEach((e) => {
      const a = e.querySelector('div.mat-sort-header-container>div.mat-sort-header-arrow');
      if (a) this.renderer.setStyle(a, 'opacity', 0);
    });
  }

  preCell(p: string, el: HTMLElement) {
    const direction = p[0] === '-' ? 'descending' : 'ascending',
      active = p[0] === '-' ? p.substr(1) : p;

    const column = el.querySelector(`mat-header-cell.mat-column-${active}`) || el.querySelector(`mat-header-cell[mat-sort-header="${active}"]`);
    if (p && column) {
      this.renderer.setAttribute(column, 'aria-sort', direction);

      const container = column.querySelector('div.mat-sort-header-container');
      this.renderer.addClass(container, 'mat-sort-header-sorted');

      const arrow = container.querySelector('div.mat-sort-header-arrow');
      if (arrow) {
        this.renderer.setStyle(arrow, 'opacity', 1);
        this.renderer.setStyle(arrow, 'transform', 'translateY(0px)');

        const indicator = arrow.querySelector('div.mat-sort-header-indicator');
        this.renderer.setStyle(indicator, 'transform', direction === 'descending' ? 'translateY(10px)' : 'translateY(0px)');

        if (direction === 'descending') {
          const left = indicator.querySelector('.mat-sort-header-pointer-left');
          this.renderer.setStyle(left, 'transform', 'rotate(45deg)');

          const right = indicator.querySelector('.mat-sort-header-pointer-right');
          this.renderer.setStyle(right, 'transform', 'rotate(-45deg)');
        }
      }
    }
  }
}
