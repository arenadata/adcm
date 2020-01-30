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
import { Directive, Output, HostListener, EventEmitter } from '@angular/core';

@Directive({
  selector: '[appScroll]',
})
export class ScrollDirective {
  private scrollTop = 0;

  @Output() read = new EventEmitter<{ direct: -1 | 1 | 0; scrollTop: number }>();

  @HostListener('scroll', ['$event.target']) onscroll(e: Element) {

    const { scrollHeight, scrollTop, clientHeight } = e;

    if (scrollTop < this.scrollTop) this.read.emit({ direct: -1, scrollTop });
    else this.read.emit( { direct: 1, scrollTop });    
    
    if (scrollHeight <= scrollTop + clientHeight) this.read.emit({ direct: 0, scrollTop });

    this.scrollTop = scrollTop;

  }
}
