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
import { Component, EventEmitter, OnDestroy, OnInit, Output } from '@angular/core';
import { FormControl } from '@angular/forms';
import { BaseDirective } from '@app/shared/directives/base.directive';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

@Component({
  selector: 'app-search',
  template: `
    <mat-form-field class="seach-field">
      <input matInput type="text" placeholder="Search field" [formControl]="search" />
      <button mat-button matSuffix mat-icon-button aria-label="Search"><mat-icon>search</mat-icon></button>
      <button mat-button matSuffix mat-icon-button aria-label="Clear" (click)="search.setValue('')">
        <mat-icon>close</mat-icon>
      </button>
    </mat-form-field>
  `,
  styles: ['mat-form-field {flex: auto;margin: 0 10px;font-size: 14px;}'],
})
export class SearchComponent extends BaseDirective implements OnInit, OnDestroy {
  search = new FormControl();
  @Output() pattern = new EventEmitter<string>();

  constructor() {
    super();
  }

  ngOnInit() {
    this.search.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        this.takeUntil()
      )
      .subscribe(value => this.pattern.emit(value));
  }
}
