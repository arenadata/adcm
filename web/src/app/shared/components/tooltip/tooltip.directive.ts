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
import { Directive, Input, ElementRef, HostListener } from '@angular/core';
import { TooltipService } from '../tooltip/tooltip.service';
import { ApiBase } from '@app/core/types/api';

@Directive({
  selector: '[appTooltip]',
})
export class TooltipDirective {
  @Input() appTooltip: string | ApiBase;
  @Input() TooltipPosition: 'top' | 'right' | 'bottom' | 'left' = 'top';
  @Input() appTooltipComponent: 'issue' | 'status' = 'issue';

  constructor(private el: ElementRef, private tooltip: TooltipService) {}

  @HostListener('mouseenter', ['$event']) menter(e: MouseEvent) {
    e.stopPropagation();
    if (this.appTooltip) this.tooltip.show(e, this.appTooltip, this.el.nativeElement, this.appTooltipComponent);
  }

  @HostListener('mousedown') mdown() {}

  @HostListener('mouseleave') mleave() {
    this.tooltip.hide();
  }
}
