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
import { Directive, Renderer2, Host, OnInit, Output, EventEmitter } from '@angular/core';
import { MatSelect } from '@angular/material/select';

@Directive({
  selector: '[appInfinityScroll]',
})
export class InfinityScrollDirective implements OnInit {
  @Output() topScrollPoint = new EventEmitter();

  constructor(private renderer: Renderer2, @Host() private matSelect: MatSelect) {}

  ngOnInit(): void {
    this.matSelect.openedChange.subscribe((open: boolean) => this.registerPanel(open));
  }

  registerPanel(open: boolean) {
    if (open) {
      const panel = this.matSelect.panel.nativeElement;
      this.renderer.listen(panel, 'scroll', this.onScrollPanel.bind(this));
    }
  }

  onScrollPanel(event: any) {
    const target = event.target;

    const height =
      Array.from<HTMLElement>(target.children).reduce((p, c) => p + c.clientHeight, 0) - target.clientHeight;
    if (target.scrollTop > height - 100) this.topScrollPoint.emit();
  }
}
