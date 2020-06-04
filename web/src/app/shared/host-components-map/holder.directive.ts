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
import { Directive, ElementRef, Input } from '@angular/core';

@Directive({
  selector: '[appHolder]',
})
export class HolderDirective {
  ps: { short: HTMLElement; long: HTMLElement };

  @Input('appHolder') set scroll(data: { direct: -1 | 1 | 0; scrollTop: number }) {
    if (data) {
      if (!this.ps) this.getPs();
      else if (this.ps.short.clientHeight + data.scrollTop < this.ps.long.clientHeight) this.ps.short.style.marginTop = `${Math.floor(data.scrollTop)}px`;
    }
  }

  constructor(private el: ElementRef) {}

  getPs() {
    const els: HTMLElement[] = [...this.el.nativeElement.children];
    if (els.length) {
      const a = els[0].querySelector<HTMLElement>('.wrapper'),
        b = els[1].querySelector<HTMLElement>('.wrapper');
      this.ps = a.clientHeight < b.clientHeight ? { short: a, long: b } : { short: b, long: a };
    }
  }
}
