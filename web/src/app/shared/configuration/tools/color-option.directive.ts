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
import { Directive, ElementRef, Input, AfterViewInit, Renderer2 } from '@angular/core';

@Directive({
  selector: '[appColorOption]'
})
export class ColorOptionDirective implements AfterViewInit {
  
  @Input('appColorOption')
  colorOption: string;

  constructor(private el: ElementRef, private render: Renderer2) { }

  ngAfterViewInit(): void {
    const pchb = this.el.nativeElement.firstElementChild;
    this.render.setStyle(pchb, 'backgroundColor', this.colorOption);
  }
}
