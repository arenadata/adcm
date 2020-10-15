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
import { BaseDirective } from '@app/shared/directives';
import { Subject } from 'rxjs';

import { ISearchParam } from '../main/main.service';

@Component({
  selector: 'app-tools',
  template: `
    <mat-form-field class="description">
      <input matInput placeholder="Description configuration" [formControl]="description" />
    </mat-form-field>
    <app-search (pattern)="search($event)"></app-search>
    <mat-checkbox [(ngModel)]="advanced" [disabled]="isAdvanced === null" [ngClass]="{ advanced: isAdvanced }">Advanced</mat-checkbox>
    <div class="control-buttons">
      <button mat-raised-button color="accent" class="form_config_button_save" [disabled]="disabledSave" (click)="onSave()">Save</button>
      <button mat-icon-button [disabled]="disabledHistory" (click)="toggleHistory()" [matTooltip]="historyShow ? 'Hide history' : 'Show history'">
        <mat-icon>history</mat-icon>
      </button>
    </div>
  `,
  styles: [
    ':host {display: flex;justify-content: space-between;align-items: baseline; margin: 10px 20px 0;}',
    '.form_config_button_save { margin: 0 16px 0 30px;}',
    '.description {flex: 0}',
  ],
})
export class ToolsComponent extends BaseDirective implements OnInit {
  private filter$ = new Subject<ISearchParam>();
  filterParams: ISearchParam = { advanced: false, search: '' };
  historyShow = false;
  isAdvanced: boolean;
  description = new FormControl();
  @Input() disabledSave = true;
  @Input() disabledHistory = true;

  @Output() applyFilter = new EventEmitter<ISearchParam>();
  @Output() save = new EventEmitter();
  @Output() showHistory = new EventEmitter<boolean>();

  ngOnInit() {
    this.filter$.pipe(this.takeUntil()).subscribe(() => this.applyFilter.emit(this.filterParams));
  }

  set advanced(advanced: boolean) {
    this.filterParams.advanced = advanced;
    this.filter$.next();
  }

  search(search: string) {
    this.filterParams.search = search;
    this.filter$.next();
  }

  toggleHistory() {
    this.historyShow = !this.historyShow;
    this.showHistory.emit(this.historyShow);
  }

  onSave() {
    this.save.emit();
  }
}
