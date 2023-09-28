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
import { Component, OnChanges, OnInit, SimpleChanges, ViewChild } from '@angular/core';
import { AbstractControl } from '@angular/forms';
import { FieldDirective } from '@app/shared/form-elements/field.directive';

import { TNReq } from '../types';
import { IYContainer, IYField, YspecService } from '../yspec/yspec.service';
import { RootComponent } from './root.component';
import { SchemeService } from './scheme.service';

@Component({
  selector: 'app-scheme',
  styles: [
    `
      div.main {
        flex: 1;
      }
      .error {
        display: block;
        margin: -20px 0 6px 10px;
      }
    `,
  ],
  template: `<div class="main">
    <app-root-scheme #root [isReadOnly]="field.read_only" [form]="current" [options]="rules" [value]="field.value || field.default" [invisibleItems]="invisibleItems"></app-root-scheme>
    <mat-error *ngIf="hasError('isEmpty')" class="error">Field [{{ field.display_name }}] is required!</mat-error>
  </div>`,
})
export class SchemeComponent extends FieldDirective implements OnInit, OnChanges {
  rules: IYField | IYContainer;
  current: AbstractControl;
  invisibleItems: string[];

  @ViewChild('root') root: RootComponent;

  constructor(private yspec: YspecService, private scheme: SchemeService) {
    super();
  }

  /**
   * after saving, the link between the form and the current (form) is lost
   * TODO: eliminate
   */
  ngOnChanges(changes: SimpleChanges): void {
    if (!changes.form.firstChange) {
      this.field.limits.rules = this.rules;
      this.form.setControl(this.field.name, this.current);
    }
  }

  ngOnInit() {
    this.yspec.Root = this.field.limits.yspec;
    this.invisibleItems = this.yspec.getInvisibleItems();
    this.rules = this.yspec.build();
    this.field.limits.rules = this.rules;
    this.rules.name = '';
    this.current = this.scheme.setCurrentForm(this.rules.type as TNReq, this.form, this.field);
  }

  /** this is using for restore default value */
  reload() {
    this.root.reload(this.field.default);
  }
}
