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
import { PreloaderService } from '@app/core';
import { Prototype, StackBase } from '@app/core/types';
import { BehaviorSubject, throwError } from 'rxjs';
import { catchError, map, tap, filter } from 'rxjs/operators';

import { InputComponent } from './input.component';
import { AddService } from '../components/add-component/add.service';
import { ButtonUploaderComponent } from './button-uploader.component';

@Component({
  selector: 'app-bundles',
  template: `
    <div class="row" [formGroup]="form">
      <mat-form-field class="full-width">
        <mat-select appInfinityScroll (topScrollPoint)="getNextPage()" required placeholder="Bundle" formControlName="prototype_id">
          <mat-option value="">...</mat-option>
          <mat-option *ngFor="let bundle of bundles$ | async" [value]="bundle.id"
            >{{ bundle.display_name }} - {{ bundle.version }} {{ bundle.bundle_edition }}</mat-option
          >
        </mat-select>
        <app-button-uploader
          [style.fontSize.px]="24"
          matSuffix
          #uploadBtn
          [color]="'accent'"
          [asIcon]="true"
          [label]="'Upload bundles'"
          (click)="$event.stopPropagation()"
          (output)="upload($event)"
        ></app-button-uploader>
        <mat-error *ngIf="isError('prototype_id')">
          <mat-error *ngIf="hasError('prototype_id', 'required')">Select a bundle.</mat-error>
        </mat-error>
      </mat-form-field>
    </div>
  `,
  styles: [],
})
export class BundlesComponent extends InputComponent implements OnInit {
  loadedBundleID: number;
  @Input() typeName: 'cluster' | 'provider';
  @ViewChild('uploadBtn', { static: true }) uploadBtn: ButtonUploaderComponent;
  bundles$ = new BehaviorSubject<StackBase[]>([]);
  page = 1;
  limit = 50;

  constructor(private preloader: PreloaderService, private service: AddService) {
    super();
  }

  ngOnInit(): void {
    this.getBundles(true);
    this.form
      .get('prototype_id')
      .valueChanges.pipe(
        filter(a => a),
        this.takeUntil()
      )
      .subscribe(a => this.service.setBundle(a, this.bundles$.getValue()));
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
        .getPrototype(this.typeName, { page: this.page - 1, limit: this.limit })
        .pipe(
          tap(a => {
            this.bundles$.next([...this.bundles$.getValue(), ...a]);
            this.selectOne(a);
          })
        )
        .subscribe();
    }
  }

  selectOne(a: Partial<Prototype>[]) {
    let id = a.length === 1 ? a[0].id : '';
    if (a.length > 1 && this.loadedBundleID) {
      const el = a.find(e => e.bundle_id === this.loadedBundleID);
      if (el) id = el.id;
    }
    this.form.get('prototype_id').setValue(id);
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
