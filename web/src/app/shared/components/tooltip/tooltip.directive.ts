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
import { Directive, ElementRef, HostListener, Input } from '@angular/core';
import { ApiBase } from '@app/core/types/api';

import { ComponentName, PositionType, TooltipService } from '../tooltip/tooltip.service';

@Directive({
  selector: '[appTooltip]',
})
export class TooltipDirective {
  @Input() appTooltip: string | ApiBase;
  @Input() appTooltipPosition: PositionType = 'bottom';
  @Input() appTooltipComponent: ComponentName;

  /**
   * TODO: To show tooltip by condition [04.12.2019]
   * ConditionType - under construction,
   * Now - one the condition this is width and scroll of source
   * tooltip.component.ts line: 118 checkBuild()
   */
  @Input() appTooltipShowByCondition: boolean;

  constructor(private el: ElementRef, private tooltip: TooltipService) {}

  @HostListener('mouseenter', ['$event']) menter(e: MouseEvent) {
    e.stopPropagation();
    const options = {
      content: this.appTooltip,
      componentName: this.appTooltipComponent,
      position: this.appTooltipPosition,
      condition: this.appTooltipShowByCondition,
    };
    if (this.appTooltip) this.tooltip.show(e, this.el.nativeElement, options);
  }

  @HostListener('mouseleave') mleave() {
    this.tooltip.hide();
  }
}
