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

import { FieldService } from '../field.service';
import { FieldComponent } from '../field/field.component';
import { GroupFieldsComponent } from '../group-fields/group-fields.component';
import { IConfig, PanelOptions } from '../types';

@Component({
  selector: 'app-config-fields',
  template: `
    <ng-container *ngFor="let panel of panels; trackBy: trackBy">
      <app-field
        class="alone"
        [form]="form"
        *ngIf="panel.options.length === 1 && !panel.options[0].subname && !panel.options[0].hidden; else more"
        [options]="panel.options[0]"
        [ngClass]="{ 'read-only': panel.options[0].disabled }"
      ></app-field>
      <ng-template #more>
        <app-group-fields *ngIf="!panel.hidden" [panel]="panel" [form]="form"></app-group-fields>
      </ng-template>
    </ng-container>
  `
})
export class ConfigFieldsComponent {
  panels: PanelOptions[] = [];
  form = new FormGroup({});

  @Output()
  event = new EventEmitter<{ name: string; data?: any }>();

  shapshot: any;

  @ViewChildren(FieldComponent)
  fields: QueryList<FieldComponent>;

  @ViewChildren(GroupFieldsComponent)
  groups: QueryList<GroupFieldsComponent>;

  @Input()
  set model(data: IConfig) {
    this.panels = this.service.getPanels(data);
    this.form = this.service.toFormGroup();
    this.shapshot = { ...this.form.value };
    this.event.emit({ name: 'load', data: { form: this.form } });
  }

  constructor(private service: FieldService) {}

  trackBy(index: number, item: PanelOptions): string {
    return item.name;
  }
}
