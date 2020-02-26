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
import { Component, OnInit, Input } from '@angular/core';
import { FormGroup, FormControl, FormArray, AbstractControl } from '@angular/forms';
import { FieldService } from '../field.service';

@Component({
  selector: 'app-root-scheme',
  template: `
    <div *ngIf="options.type === 'list'">
      <label>{{ options.name }} :: {{ options.type }}</label>
      <button mat-icon-button color="accent" (click)="add()">
        <mat-icon>add_circle_outline</mat-icon>
      </button>
    </div>
    <div class="content" [formGroup]="form">

      <ng-container *ngIf="options.type === 'list'">
        <ng-container *ngFor="let item of form.controls; let i = index">
          <ng-container *ngIf="notSimple(item)">
            <app-root-scheme [form]="item" [options]="rules">
              <button mat-icon-button color="primary" (click)="remove(i)"><mat-icon>highlight_off</mat-icon></button>
            </app-root-scheme>
          </ng-container>
        </ng-container>
      </ng-container>

      <div style="display: flex;" *ngIf="options.type === 'dict'">
        <div style="flex: 1">
          <ng-container *ngFor="let item of dict">
            <ng-container *ngIf="notSimpleDict(item); else simpleo">
              <app-root-scheme [form]="getForm(item)" [options]="rules"></app-root-scheme>
            </ng-container>
            <ng-container #simpleo *ngTemplateOutlet="simple; context: { item: item }"></ng-container>
          </ng-container>          
        </div>
        <ng-content></ng-content>
      </div>

      <ng-template #simple let-item="item">
        <mat-form-field style="margin: 6px 0 0; width: 100%">
          <mat-label>{{ item }}</mat-label>
          <input matInput placeholder="" [formControlName]="item" />
        </mat-form-field>
      </ng-template>

      {{ form.value | json }}
    </div>
  `,
  styleUrls: ['./scheme.component.scss']
})
export class RootComponent implements OnInit {
  @Input() form: FormGroup | FormArray;
  @Input() options: any;

  constructor(private service: FieldService) {}

  container: FormArray | FormGroup;

  dict: string[];

  notSimple(item: AbstractControl) {
    return 'controls' in item;
  }

  notSimpleDict(name: string) {
    return 'controls' in this.getForm(name);
  }

  getForm(name: string) {
    return (this.form as FormGroup).controls[name];
  }

  ngOnInit(): void {

    if (this.options.type === 'dict') {
      this.container = this.form as FormGroup;
      this.dict = Object.keys(this.container.controls);
    }

    //if (!this.form.controls[this.options.name]) this.form.addControl(this.options.name, this.container);
  }

  remove(i: number) {
    (this.form as FormArray).removeAt(i);
  }

  add() {
    if (this.rules.type === 'dict') {
      const item = new FormGroup({});
      this.itemRules.map(x => item.addControl(x.name, new FormControl('', this.service.setValidator(x))));
      (this.form as FormArray).push(item);
    }
  }

  get rules() {
    return this.options.options[0];
  }

  get itemRules() {
    return this.rules.options[0];
  }

  get isValid() {
    return true;
  }

  hasError(title: string) {}
}
