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
import { Directive, HostListener, ContentChild, Renderer2 } from '@angular/core';
import { MatIcon } from '@angular/material';

@Directive({
  selector: '[appHoverStatusTask]'
})
export class HoverDirective {
  @ContentChild('taskIcon') icon: MatIcon;
  @HostListener('mouseover') onHover() {
    const icon = this.icon._elementRef.nativeElement;
    this.re.removeClass(icon, 'icon-locked');
    icon.innerText = 'block';
  }
  @HostListener('mouseout') onOut() {
    const icon = this.icon._elementRef.nativeElement;
    this.re.addClass(icon, 'icon-locked');
    icon.innerText = 'autorenew';
  }
  constructor(private re: Renderer2) {}
}
