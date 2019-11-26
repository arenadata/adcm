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
import { Component, EventEmitter, Input, Output, QueryList, ViewChildren } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { IConfig, FieldOptions, FieldStack } from '@app/core/types';

import { FieldService, PanelInfo } from '../field.service';
import { FieldComponent } from '../field/field.component';
import { GroupFieldsComponent } from '../group-fields/group-fields.component';

@Component({
  selector: 'app-config-fields',
  template: `
    <ng-container *ngFor="let panel of panels">
      <app-field
        class="alone"
        *ngIf="panel.options.length === 1 && !panel.options[0].subname; else more"
        [form]="form"
        [options]="panel.options[0]"
        [ngClass]="{ 'read-only': panel.options[0].disabled }"
      ></app-field>
      <ng-template #more>
        <app-group-fields *ngIf="!panel.hidden" [panel]="panel" [form]="form" [globalConfig]="globalConfig"></app-group-fields>
      </ng-template>
    </ng-container>
  `,
})
export class ConfigFieldsComponent {
  panels: PanelInfo[] = [];
  fieldsData: FieldOptions[] = [];

  @Output()
  event = new EventEmitter<{ name: string; data?: any }>();

  form: FormGroup = new FormGroup({});
  shapshot: any;

  @ViewChildren(FieldComponent)
  fields: QueryList<FieldComponent>;

  @ViewChildren(GroupFieldsComponent)
  groups: QueryList<GroupFieldsComponent>;

  globalConfig: IConfig;

  @Input()
  set model(data: IConfig) {
    this.globalConfig = data;
    this.panels = [];
    Object.keys(this.form.controls).map(name => this.form.removeControl(name));
    if (data && data.config.length) {
      this.fieldsData = data.config.filter(a => a.type !== 'group').map((a: FieldStack) => this.service.getFieldBy(a));

      this.panels = data.config
        .filter(a => a.type === 'group' || !a.subname)
        .map(a => ({
          name: a.name,
          title: a.display_name,
          read_only: a.read_only,
          hidden: a.ui_options ? !!a.ui_options['invisible'] || !!a.ui_options['advanced'] : false,
          ui_options: a.ui_options,
          options: this.fieldsData.filter(b => b.name === a.name),
          activatable: a.activatable,
          description: a.description,
        }));

      this.service.toFormGroup(this.fieldsData, this.form);
      Object.keys(this.form.controls).forEach(controlName => this.form.controls[controlName].markAsTouched());
      setTimeout(() => (this.shapshot = { ...this.form.value }), 0);
      this.event.emit({ name: 'load', data: { form: this.form } });
    }
  }

  constructor(private service: FieldService) {}
}
