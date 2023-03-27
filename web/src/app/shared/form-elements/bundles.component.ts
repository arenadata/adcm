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
import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { FormControl } from '@angular/forms';
import { Prototype, StackBase } from '@app/core/types';
import { of } from 'rxjs';
import {filter, map, switchMap, tap} from 'rxjs/operators';
import { EventHelper } from '@app/adwp';

import { AddService } from '../add-component/add.service';
import { ButtonUploaderComponent } from './button-uploader.component';
import { InputComponent } from './input.component';

@Component({
  selector: 'app-bundles',
  template: `
    <div class="row" [formGroup]="form">
      <mat-form-field>
        <mat-select appInfinityScroll (topScrollPoint)="getNextPage()" required placeholder="Bundle" formControlName="display_name">
          <mat-option value="">...</mat-option>
          <mat-option *ngFor="let bundle of bundles" [value]="bundle.display_name"> {{ bundle.display_name }} </mat-option>
        </mat-select>
      </mat-form-field>
      &nbsp;&nbsp;
      <mat-form-field>
        <mat-select placeholder="Version" required formControlName="bundle_id">
          <mat-option *ngFor="let bundle of versions" [value]="bundle.bundle_id"> {{ bundle.version }} {{ bundle.bundle_edition }} </mat-option>
        </mat-select>
      </mat-form-field>

      <app-button-uploader
        [style.fontSize.px]="24"
        #uploadBtn
        [color]="'accent'"
        [asIcon]="true"
        [label]="'Upload bundles'"
        (click)="EventHelper.stopPropagation($event)"
        (output)="upload($event)"
      ></app-button-uploader>
    </div>
  `,
  styles: ['.row { align-items: center;display:flex; }', 'mat-form-field {flex: 1}'],
})
export class BundlesComponent extends InputComponent implements OnInit {
  EventHelper = EventHelper;

  @Input() typeName: 'cluster' | 'provider';
  @ViewChild('uploadBtn', { static: true }) uploadBtn: ButtonUploaderComponent;
  loadedBundle: { bundle_id: number; display_name: string };
  bundles: StackBase[] = [];
  versions: StackBase[];
  page = 1;
  limit = 50;
  disabledVersion = true;
  elementName = null;

  @Output() prototypeChanged = new EventEmitter();

  constructor(private service: AddService) {
    super();
  }

  ngOnInit(): void {
    this.form.addControl('display_name', new FormControl());
    this.form.addControl('bundle_id', new FormControl());

    this.getBundles();

    this.form
      .get('display_name')
      .valueChanges.pipe(
        this.takeUntil(),
        tap((elementName) => this.elementName = elementName),
        switchMap((elementName) => (elementName ? this.service.getPrototype(this.typeName, { page: 0, limit: 500, ordering: '-version', display_name: elementName }) : of([])))
      )
      .subscribe((elements) => {
        this.versions = elements.filter((element) => element.display_name === this.elementName);
        this.selectOne(this.versions, 'bundle_id');
        this.loadedBundle = null;
      });

    // for check license agreement
    this.form
      .get('bundle_id')
      .valueChanges.pipe(
        this.takeUntil(),
        filter((a) => a)
      )
      .subscribe((id) => {
        const prototype = this.versions.find((b) => b.bundle_id === +id);
        this.service.currentPrototype = prototype;
        this.prototypeChanged.emit(prototype);
        this.form.get('prototype_id').setValue(this.service.currentPrototype.id);
      });
  }

  getNextPage() {
    const count = this.bundles.length;
    if (count === this.page * this.limit) {
      this.page++;
      this.getBundles();
    }
  }

  getBundles() {
    const offset = (this.page - 1) * this.limit;
    const params = { fields: 'display_name', distinct: 1, ordering: 'display_name', limit: this.limit, offset };
    this.service.getPrototype(this.typeName, params).subscribe((bundles) => {
      this.bundles = [...new Map([...this.bundles, ...bundles].map((item) => [item["display_name"], item])).values()];
      this.selectOne(bundles, 'display_name');
    });
  }

  selectOne(a: Partial<Prototype>[] = [], formName: string) {
    const el = this.loadedBundle ? a.find((e) => e[formName] === this.loadedBundle[formName]) : null;
    const id = el ? el[formName] : a.length ? (formName === 'bundle_id' || a.length === 1 ? a[0][formName] : '') : '';
    this.form.get(formName).setValue(id);
  }

  upload(data: FormData[]) {
    this.service
      .upload(data)
      .pipe(map((a) => a.map((e) => ({ bundle_id: e.id, display_name: e.display_name, version: e.version }))))
      .subscribe((a) => {
        this.loadedBundle = a[0];
        this.uploadBtn.fileUploadInput.nativeElement.value = '';
        this.page = 0;
        this.bundles = [];
        this.getBundles();
      });
  }
}
