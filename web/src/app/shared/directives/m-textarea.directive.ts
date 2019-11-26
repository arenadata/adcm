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
import { Directive, ElementRef, HostListener, Input, OnDestroy, OnInit } from '@angular/core';
import { getProfile, ProfileService, ProfileState, setTextareaHeight } from '@app/core/store';
import { Store } from '@ngrx/store';

import { BaseDirective } from './base.directive';

// textarea Material
const PADDING_TOP_BOTTOM = 16;

@Directive({
  selector: '[appMTextarea]',
  providers: [ProfileService],
})
export class MTextareaDirective extends BaseDirective implements OnInit, OnDestroy {
  flag = false;
  @Input('appMTextarea')
  key: string;

  constructor(private el: ElementRef, private profile: Store<ProfileState>) {
    super();
  }

  @HostListener('mousedown')
  mouseDown() {
    this.flag = true;
  }

  ngOnInit(): void {
    window.addEventListener('mouseup', () => {
      this.profile
        .select(getProfile)
        .pipe(this.takeUntil())
        .subscribe(p => {
          const data = p.textarea;
          const old = data[this.key];
          const value = +this.el.nativeElement.offsetHeight - PADDING_TOP_BOTTOM;
          if (this.flag && old !== value) this.profile.dispatch(setTextareaHeight({ key: this.key, value }));
          this.flag = false;
        });
    });

    this.profile
      .select(getProfile)
      .pipe(this.takeUntil())
      .subscribe(p => {
        const k = Object.keys(p.textarea).find(key => key === this.key);
        if (k) (this.el.nativeElement as HTMLTextAreaElement).style.height = p.textarea[k] + 'px';
      });
  }
}
