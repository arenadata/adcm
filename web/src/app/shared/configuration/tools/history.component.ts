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
import { Observable } from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { ConfigFieldsComponent as FieldsComponent } from '../fields/fields.component';
import { CompareConfig, FieldOptions, IConfig, PanelOptions } from '../types';

@Component({
  selector: 'app-history',
  template: `
    <mat-toolbar>
      <mat-form-field>
        <mat-select placeholder="History" [value]="versionID" (valueChange)="changeVersion($event)">
          <mat-option *ngFor="let item of history$ | async; trackBy: trackById" [value]="item.id"> {{ item.date | date: 'short' }} {{ item.description }} </mat-option>
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
  @Output() version = new EventEmitter<number>();

  iconDisabled = true;
  history$: Observable<CompareConfig[]>;
  comparator = new FormControl();
  compare: CompareConfig[];
  current: IConfig;

  constructor(private api: ApiService) {
    super();
  }

  trackById(item: CompareConfig): number {
    return item.id;
  }

  ngOnInit() {
    this.getData();

    /**  */
    this.comparator.valueChanges.pipe(this.takeUntil()).subscribe((configIDs: number[]) => {
      this.clearCompare(configIDs);
      this.checkValue(configIDs.map((id) => this.compare.find((a) => a.id === id)));
    });
  }

  getData() {
    this.history$ = this.api.get<IConfig[]>(this.historyUrl).pipe(
      tap((history) => (this.current = history.find((a) => a.id === this.versionID))),
      map((history) => history.filter((a) => a.id !== this.versionID).map((b) => ({ ...b, color: getRandomColor() }))),
      tap((a) => {
        this.compare = a;
        this.iconDisabled = a.length < 1;
      })
    );
  }

  clearCompare(configIDs: number[]) {
    this.fields.dataOptions.map((a) => this.runClear(a, configIDs));
  }

  runClear(a: FieldOptions | PanelOptions, configIDs: number[]) {
    if ('options' in a) a.options.map((b) => this.runClear(b, configIDs));
    else if (a.compare.length) a.compare = a.compare.filter((b) => configIDs.includes(b.id));
    return a;
  }

  checkValue(configs: CompareConfig[]) {
    this.fields.dataOptions.map((a) => this.runCheck(a, configs));
  }

  runCheck(a: FieldOptions | PanelOptions, configs: CompareConfig[]) {
    if ('options' in a) a.options.map((b) => this.runCheck(b, configs));
    else this.checkField(a, configs);
    return a;
  }

  checkField(a: FieldOptions, configs: CompareConfig[]) {
    configs
      .filter((b) => a.compare.every((e) => e.id !== b.id))
      .map((c) => {
        const co = this.findOldField(a.key, c);
        if (co && (String(co.value) !== String(a.value) || (isObject(a.value) && JSON.stringify(a.value) !== JSON.stringify(co.value)))) a.compare.push(co);
      });
    return a;
  }

  findOldField(key: string, cc: CompareConfig) {
    const value = key
      .split('/')
      .reverse()
      .reduce((p, c) => p[c], cc.config);
    if (value !== null && value !== undefined && String(value)) {
      const { id, date, color } = { ...cc };
      return { id, date, color, value };
    }
  }

  changeVersion(id: number) {
    this.version.emit(id);
  }
}
