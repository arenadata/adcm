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
import { Component, OnInit } from '@angular/core';
import { PreloaderService } from '@app/core/services';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

@Component({
  selector: 'app-progress',
  template: `
    <mat-progress-bar
      mode="indeterminate"
      class="progress-bar"
      [class.hidden]="(show$ | async) === false"
    ></mat-progress-bar>
  `,
  styles: ['.progress-bar {position: absolute;width: 100%;height: 3px;z-index: 3;}'],
})
export class ProgressComponent implements OnInit {
  show$: Observable<boolean> = of(false);
  constructor(private preloader: PreloaderService) {}
  ngOnInit() {
    this.show$ = this.preloader.active$.pipe(delay(1));
  }
}
