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
import { Directive, ElementRef, Input, Renderer2 } from '@angular/core';

@Directive({
  selector: '[appMultiSort]',
})
export class MultiSortDirective {
  @Input('appMultiSort') set sortParam(param: string) {
    const el = this.el.nativeElement;
    Array.from<HTMLElement>(el.getElementsByTagName('mat-header-cell')).forEach(e => {
      const a = e.querySelector('div.mat-sort-header-container>div.mat-sort-header-arrow');
      if (a) this.renderer.setStyle(a, 'opacity', 0);
    });
    setTimeout(() => {
      param.split(',').forEach(cell => {
        const direction = cell[0] === '-' ? 'descending' : 'ascending',
          active = cell[0] === '-' ? cell.substr(1) : cell;
        const c = el.querySelector(`mat-header-cell.mat-column-${active}`);
        if (c) {
          this.renderer.setAttribute(c, 'aria-sort', direction);
          const cont = c.querySelector('div.mat-sort-header-container');
          this.renderer.addClass(cont, 'mat-sort-header-sorted');
          const arrow = cont.querySelector('div.mat-sort-header-arrow');

          this.renderer.setStyle(arrow, 'opacity', 1);
          this.renderer.setStyle(arrow, 'transform', 'translateY(0px)');

          const ind = arrow.querySelector('div.mat-sort-header-indicator');
          this.renderer.setStyle(ind, 'transform', direction === 'descending' ? 'translateY(10px)' : 'translateY(0px)');
          if (direction === 'descending') {
            const left = ind.querySelector('.mat-sort-header-pointer-left');
            this.renderer.setStyle(left, 'transform', 'rotate(45deg)');
            const right = ind.querySelector('.mat-sort-header-pointer-right');
            this.renderer.setStyle(right, 'transform', 'rotate(-45deg)');
          }
        }
      });
    }, 500);
  }

  constructor(private el: ElementRef, private renderer: Renderer2) {}
}
