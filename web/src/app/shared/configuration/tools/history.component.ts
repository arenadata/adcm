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
import { ApiService } from '@app/core/api';
import { getRandomColor, isObject } from '@app/core/types';
import { BaseDirective } from '@app/shared/directives/base.directive';
import { forkJoin, Observable } from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { CompareConfig } from '../field.service';
import { FieldComponent } from '../field/field.component';
import { ConfigFieldsComponent as FieldsComponent } from '../fields/fields.component';
import { IConfig } from '../types';

@Component({
  selector: 'app-history',
  template: `
    <mat-toolbar>
      <mat-form-field>
        <mat-select placeholder="History" [value]="versionID" (valueChange)="changeVersion($event)">
          <mat-option *ngFor="let item of history$ | async; trackBy: trackById" [value]="item.id">
            {{ item.date | date: 'short' }} {{ item.description }}
          </mat-option>
        </mat-select>
      </mat-form-field>
      <span>&nbsp;&nbsp;</span>
      <mat-form-field>
        <mat-select placeholder="Compare to" [formControl]="comparator" multiple>
          <mat-option *ngFor="let item of compare; trackBy: trackById" [value]="item.id" [appColorOption]="item.color">
            {{ item.date | date: 'short' }}
            {{ item.description }}
          </mat-option>
        </mat-select>
      </mat-form-field>
    </mat-toolbar>
  `,
  styles: [':host {height: 64px;}', 'mat-form-field {flex: auto; margin: 0 10px; font-size: 14px; }'],
})
export class HistoryComponent extends BaseDirective implements OnInit {
  @Input() fields: FieldsComponent;
  @Input() versionID: number;
  @Input() historyUrl: string;
  @Output() version = new EventEmitter<{ id: number }>();

  iconDisabled = true;
  history$: Observable<CompareConfig[]>;
  comparator = new FormControl();
  compare: CompareConfig[];

  constructor(private api: ApiService) {
    super();
  }

  trackById(item: CompareConfig): number {
    return item.id;
  }

  ngOnInit() {
    this.getData();

    /** toolbar comparator current with history item */
    this.comparator.valueChanges.pipe(this.takeUntil()).subscribe((valueChange: number[]) => {
      this.fields.fields.map(f => this.clearCheck(f, valueChange));
      this.fields.groups.forEach(g => g.fields.map(f => this.clearCheck(f, valueChange)));

      /** 
       * TODO: excessive requests
      */
      const comp = valueChange.map(id => this.compare.find(a => a.id === id));

      forkJoin(
        comp.map(config =>
          this.api.get<IConfig>(`${this.historyUrl}${config.id}/`).pipe(
            tap(v => {
              this.fields.fields.filter(c => c.options.name !== '__main_info').map(c => this.checkField(v, c, config));
              this.fields.groups.forEach(g => g.fields.filter(c => c.options.type !== 'group').map(c => this.checkField(v, c, config)));
            })
          )
        )
      )
        .pipe(this.takeUntil())
        .subscribe();
    });
  }

  getData() {
    this.history$ = this.api.get<IConfig[]>(this.historyUrl).pipe(
      map(history => history.filter(a => a.id !== this.versionID).map(b => ({ ...b, color: getRandomColor() }))),
      tap(a => {
        this.compare = a;
        this.iconDisabled = a.length < 1;
      })
    );
  }

  clearCheck(field: FieldComponent, valueChange: number[]) {
    field.clearCompare(valueChange);
    field.cdetector.markForCheck();
  }

  checkField(c: IConfig, field: FieldComponent, config: CompareConfig) {
    const stack = c.config.find(a => a.name === field.options.name && a.subname === field.options.subname && !field.options.hidden);
    if (
      stack &&
      (String(stack.value) !== String(field.options.value) || (isObject(stack.value) && JSON.stringify(stack.value) !== JSON.stringify(field.options.value)))
    ) {
      field.addCompare({ config, stack });
      field.cdetector.markForCheck();
    }
  }

  changeVersion(id: number) {
    this.version.emit({ id });
  }
}
