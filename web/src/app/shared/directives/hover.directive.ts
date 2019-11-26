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
import { Directive, HostListener, ElementRef } from '@angular/core';

@Directive({
  selector: '[appHover]',
})
export class HoverDirective {
  constructor(private el: ElementRef) {}

  @HostListener('mouseenter')
  onmouseenter() {
    this.el.nativeElement.style.backgroundColor = 'rgba(255, 255, 255, 0.12)';
    this.el.nativeElement.style.cursor = 'pointer';
  }

  @HostListener('mouseleave')
  onmouseleave() {
    this.el.nativeElement.style.backgroundColor = 'transparent';
    this.el.nativeElement.style.cursor = 'defautl';
  }
}
