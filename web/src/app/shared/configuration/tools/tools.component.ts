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
      <input matInput placeholder="Description configuration" [formControl]="descriptionFormControl" [value]="description" />
    </mat-form-field>
    <app-search (pattern)="filter($event)"></app-search>
    <mat-checkbox [(ngModel)]="advanced" [ngClass]="{ advanced: isAdvanced }">Advanced</mat-checkbox>
    <div class="control-buttons">
      <button mat-raised-button color="accent" class="form_config_button_save" [disabled]="disabledSave" (click)="save()">
        Save
      </button>
      <button mat-icon-button [disabled]="disabledHistory" (click)="toggleHistory()" [matTooltip]="historyShow ? 'Hide history' : 'Show history'">
        <mat-icon>history</mat-icon>
      </button>
    </div>
  `,
  styles: [':host {display: flex;justify-content: space-between;align-items: baseline;}', '.form_config_button_save { margin: 0 16px 0 30px;}', '.description {flex: 0}'],
})
export class ToolsComponent extends BaseDirective implements OnInit {
  historyShow = false;
  descriptionFormControl = new FormControl();
  private _advanced = false;
  private _search = '';
  private _filter = new Subject<ISearchParam>();

  @Input() description = '';
  @Input() disabledSave = true;
  @Input() disabledHistory = true;
  @Input() isAdvanced = false;
  @Output() onfilter = new EventEmitter<ISearchParam>();
  @Output() onsave = new EventEmitter();
  @Output() onhistory = new EventEmitter<boolean>();

  ngOnInit() {
    this._filter.pipe(this.takeUntil()).subscribe(() => this.onfilter.emit({ advanced: this._advanced, search: this._search }));
  }

  set advanced(advanced: boolean) {
    this._advanced = advanced;
    this._filter.next({ advanced, search: this._search });
  }

  filter(search: string) {
    this._search = search;
    this._filter.next({ advanced: this._advanced, search });
  }

  toggleHistory() {
    this.historyShow = !this.historyShow;
    this.onhistory.emit(this.historyShow);
  }

  save() {
    this.onsave.emit();
  }
}
