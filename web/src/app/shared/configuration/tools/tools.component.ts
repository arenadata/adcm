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
import { Component, OnInit, EventEmitter, Output, Input } from '@angular/core';
import { FormControl } from '@angular/forms';
import { Subject } from 'rxjs';
import { BaseDirective } from '@app/shared/directives';
import { IToolsEvent } from '../field.service';

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
      <button mat-icon-button [disabled]="disabledHistory" (click)="history()" [matTooltip]="historyShow ? 'Hide history' : 'Show history'">
        <mat-icon>history</mat-icon>
      </button>
    </div>
  `,
  styles: [':host {display: flex;justify-content: space-between;align-items: baseline;}', '.form_config_button_save { margin: 0 16px 0 30px;}']
})
export class ToolsComponent extends BaseDirective implements OnInit {
  historyShow = false;
  descriptionFormControl = new FormControl();
  private _advanced = false;
  private _search = '';
  private _filter = new Subject<{ a: boolean; s: string }>();

  @Input() description = '';
  @Input() disabledSave = true;
  @Input() disabledHistory = true;
  @Input() isAdvanced = false;
  @Output() event = new EventEmitter<IToolsEvent>();

  ngOnInit() {
    this._filter.pipe(this.takeUntil()).subscribe(() => this.event.emit({ name: 'filter', conditions: { advanced: this._advanced, search: this._search } }));
  }

  set advanced(value: boolean) {
    this._advanced = value;
    this._filter.next({ a: this._advanced, s: this._search });
  }

  filter(value: string) {
    this._search = value;
    this._filter.next({ a: this._advanced, s: this._search });
  }

  history() {
    this.historyShow = !this.historyShow;
    this.event.emit({ name: 'history', conditions: this.historyShow });
  }

  save() {
    this.event.emit({ name: 'save' });
  }
}
