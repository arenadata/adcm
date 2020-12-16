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
import { Component, Input, OnInit } from '@angular/core';
import { AbstractControl, FormControl, FormGroup, ValidatorFn } from '@angular/forms';
import { MatCheckboxChange } from '@angular/material/checkbox';
import { ChannelService, ClusterService, keyChannelStrim } from '@app/core';
import { IExport, IImport } from '@app/core/types';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

interface IComposite {
  [key: string]: number;
}

const trueOnly = (): ValidatorFn => (control: AbstractControl): { [key: string]: any } | null => (control.value ? null : { trueOnly: !control.value });

const requiredObject = (): ValidatorFn => (control: AbstractControl): { [key: string]: boolean } | null =>
  Object.keys(control.value).some((key) => control.value[key]) ? null : { requiered: true };

@Component({
  selector: 'app-exports',
  template: `
    <ng-container [formGroup]="form">
      <ng-container [formGroupName]="getKey({ import_id: import.id })">
        <div *ngFor="let item of import.exports" class="component">
          <mat-checkbox [checked]="item.binded" [formControlName]="getKey(item.id)" (change)="change($event, item)"> {{ item.obj_name }}</mat-checkbox>
          <div>{{ item.bundle_name }} {{ item.bundle_version }}</div>
        </div>
      </ng-container>
    </ng-container>
  `,
  styles: ['.component {padding: 6px 8px; margin-bottom: 18px; font-size: 18px;}', '.component div {font-size: 12px;margin-left: 24px; margin-top: 4px;}'],
})
export class ExportComponent {
  @Input() form: FormGroup;
  @Input() import: IImport;

  getKey(id: IComposite) {
    return JSON.stringify(id);
  }

  change(e: MatCheckboxChange, item: IExport) {
    if (!this.import.multibind) {
      const group = this.form.controls[this.getKey({ import_id: this.import.id })] as FormGroup;

      if (e.checked)
        Object.keys(group.controls)
          .map((key) => {
            group.controls[key].clearValidators();
            return key;
          })
          .filter((key) => key !== this.getKey(item.id))
          .map((key) => group.controls[key].setValue(false));
      else if (this.import.required) {
        Object.keys(group.controls).map((key) => {
          const c = group.controls[key];
          c.setValidators(trueOnly());
          c.updateValueAndValidity();
        });
      }
    }
  }
}

@Component({
  selector: 'app-import',
  template: `
    <p class="controls" *ngIf="asIs">
      <button mat-raised-button color="accent" (click)="go()" [disabled]="form.invalid">Save</button>
    </p>
    <div class="items">
      <div *ngFor="let item of data$ | async" class="group">
        <h3>
          {{ item.name }}
          <mat-error *ngIf="hasError(item.id)">This import is required!</mat-error>
        </h3>
        <app-exports [import]="item" [form]="form"></app-exports>
      </div>
    </div>
  `,
  styleUrls: ['./import.component.scss'],
})
export class ImportComponent implements OnInit {
  form = new FormGroup({});
  data$: Observable<IImport[]>;
  asIs = false;

  constructor(private current: ClusterService, private channel: ChannelService) {}

  getKey(id: IComposite) {
    return JSON.stringify(id);
  }

  hasError(id: number) {
    return this.form.get(this.getKey({ import_id: id })).invalid;
  }

  ngOnInit() {
    this.data$ = this.current.getImportData().pipe(
      tap((a) => (this.asIs = !!a.length)),
      tap((a) =>
        a.map((i: IImport) => {
          const validFlag = i.required && !i.multibind && i.exports.every((e) => !e.binded);
          const exportGroup = i.exports.reduce((p, c) => {
            const fc = {};
            fc[`${this.getKey(c.id)}`] = new FormControl(c.binded, validFlag ? trueOnly() : null);
            return { ...p, ...fc };
          }, {});
          const import_id = this.getKey({ import_id: i.id });
          this.form.addControl(import_id, new FormGroup(exportGroup, i.required ? requiredObject() : null));
        })
      )
    );
  }

  go() {
    if (!this.form.invalid) {
      let bind = [];
      Object.keys(this.form.controls)
        .filter((a) => Object.keys(this.form.controls[a].value).length)
        .map((key) => {
          const obj = JSON.parse(key);
          const value = this.form.controls[key].value;
          const items = Object.keys(value)
            .filter((a) => value[a] === true)
            .map((a) => ({ ...obj, export_id: JSON.parse(a) }));
          bind = [...bind, ...items];
        });
      this.current.bindImport({ bind }).subscribe((_) => this.channel.next(keyChannelStrim.notifying, 'Successfully saved'));
    }
  }
}
