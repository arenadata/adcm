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
import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { FormControl } from '@angular/forms';
import { PreloaderService } from '@app/core';
import { Prototype, StackBase } from '@app/core/types';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';

import { AddService } from '../add-component/add.service';
import { ButtonUploaderComponent } from './button-uploader.component';
import { InputComponent } from './input.component';

@Component({
  selector: 'app-bundles',
  template: `
    <div class="row" [formGroup]="form">
      <mat-form-field>
        <mat-select appInfinityScroll (topScrollPoint)="getNextPage()" required placeholder="Bundle" formControlName="prototype_name">
          <mat-option value="">...</mat-option>
          <mat-option *ngFor="let bundle of bundles$ | async" [value]="bundle.display_name"> {{ bundle.display_name }} [ {{ bundle.bundle_edition }} ] </mat-option>
        </mat-select>
      </mat-form-field>
      &nbsp;&nbsp;
      <mat-form-field>
        <mat-select placeholder="Version" required formControlName="prototype_id">
          <mat-option *ngFor="let bundle of versions" [value]="bundle.id">
            {{ bundle.version }}
          </mat-option>
        </mat-select>
      </mat-form-field>

      <app-button-uploader
        [style.fontSize.px]="24"
        #uploadBtn
        [color]="'accent'"
        [asIcon]="true"
        [label]="'Upload bundles'"
        (click)="$event.stopPropagation()"
        (output)="upload($event)"
      ></app-button-uploader>
    </div>
  `,
  styles: ['.row { align-items: center; }', 'mat-form-field {flex: 1}']
})
export class BundlesComponent extends InputComponent implements OnInit {
  loadedBundleID: number;
  @Input() typeName: 'cluster' | 'provider';
  @ViewChild('uploadBtn', { static: true }) uploadBtn: ButtonUploaderComponent;
  bundles$ = new BehaviorSubject<StackBase[]>([]);
  page = 1;
  limit = 50;

  disabledVersion = true;
  versions: StackBase[];

  constructor(private preloader: PreloaderService, private service: AddService) {
    super();
  }

  ngOnInit(): void {
    this.form.addControl('prototype_name', new FormControl());

    this.getBundles(true);

    const forVersion$ = (display_name: string) => {
      return display_name ? this.service.getPrototype(this.typeName, { page: 0, limit: 500, display_name }) : of([]);
    };

    this.form
      .get('prototype_name')
      .valueChanges.pipe(
        this.takeUntil(),
        switchMap(a => forVersion$(a))
      )
      .subscribe(a => {
        this.versions = a;
        this.selectOne(a, 'prototype_id', 'id');
        this.loadedBundleID = null;
      });

    // for check license agreement
    this.form
      .get('prototype_id')
      .valueChanges.pipe(this.takeUntil())
      .subscribe(a => this.service.setBundle(a, this.versions));
  }

  getNextPage() {
    const count = this.bundles$.getValue().length;
    if (count === this.page * this.limit) {
      this.page++;
      this.getBundles(true);
    }
  }

  getBundles(isOpen: boolean) {
    if (isOpen) {
      this.preloader.freeze();
      this.service
        .getPrototype(this.typeName, { page: this.page - 1, limit: this.limit, fields: 'display_name', distinct: 1 })
        .pipe(
          tap(a => {
            this.bundles$.next([...this.bundles$.getValue(), ...a]);
            this.selectOne(a, 'prototype_name', 'display_name');
          })
        )
        .subscribe();
    }
  }

  selectOne(a: Partial<Prototype>[] = [], formName: string, propName: string) {
    const el = a.find(e => e.bundle_id === this.loadedBundleID);
    const id = el ? el[propName] : a.length ? (propName === 'id' || a.length === 1 ? a[0][propName] : '') : '';
    this.form.get(formName).setValue(id);
  }

  upload(data: FormData[]) {
    this.service
      .upload(data)
      .pipe(
        catchError(e => throwError(e)),
        map(a => a.map(e => ({ id: e.id, display_name: e.display_name, version: e.version })))
      )
      .subscribe(a => {
        this.loadedBundleID = (<any>a[0]).id;
        this.uploadBtn.fileUploadInput.nativeElement.value = '';
        this.page = 0;
        this.bundles$.next([]);
        this.getBundles(true);
      });
  }
}
