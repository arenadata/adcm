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
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormControl } from '@angular/forms';
import { BaseDirective } from '@app/shared/directives/base.directive';

import { CompareConfig } from '../types';

@Component({
  selector: 'app-history',
  template: `
    <mat-toolbar>
      <mat-form-field>
        <mat-select #vs placeholder="History" [formControl]="historyVersion">
          <mat-option *ngFor="let item of compareConfig; trackBy: trackById" [value]="item.id">[#{{ item.id }}] - {{ item.date | date: 'short' }} {{ item.description }} </mat-option>
        </mat-select>
      </mat-form-field>
      <span>&nbsp;&nbsp;</span>
      <mat-form-field>
        <mat-select placeholder="Compare to" [formControl]="comparator" multiple>
          <mat-option *ngFor="let item of currentCompareConfig; trackBy: trackById" [value]="item.id" [appColorOption]="item.color">
            [#{{ item.id }}] - {{ item.date | date: 'short' }} {{ item.description }}
          </mat-option>
        </mat-select>
      </mat-form-field>
    </mat-toolbar>
  `,
  styles: [':host {height: 64px;}', 'mat-form-field {flex: auto; margin: 0 10px; font-size: 14px; }'],
})
export class HistoryComponent extends BaseDirective implements OnInit {
  @Input() compareConfig: CompareConfig[];
  @Input() currentVersion: number;
  @Output() version = new EventEmitter<number>();
  @Output() compare = new EventEmitter<number[]>();

  historyVersion = new FormControl();
  comparator = new FormControl();

  get currentCompareConfig() {
    return this.compareConfig ? this.compareConfig.filter((config) => config.id !== this.currentVersion) : [];
  }

  ngOnInit() {
    this.comparator.valueChanges.pipe(this.takeUntil()).subscribe((ids: number[]) => this.compare.emit(ids));
    this.historyVersion.valueChanges.pipe(this.takeUntil()).subscribe((id: number) => this.version.emit(id));
  }

  changeVersion(id: number) {
    this.version.emit(id);
  }

  trackById(item: CompareConfig): number {
    return item.id;
  }

  reset() {
    this.comparator.reset();
  }
}
