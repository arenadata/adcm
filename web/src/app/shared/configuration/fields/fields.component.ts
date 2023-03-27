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

import { ChannelService, FullyRenderedService, keyChannelStrim } from '@app/core/services';
import { FieldService, TFormOptions } from '../services/field.service';
import { FieldComponent } from '../field/field.component';
import { GroupFieldsComponent } from '../group-fields/group-fields.component';
import { IConfig, IPanelOptions } from '../types';
import { BaseDirective } from '@app/adwp';
import { FormGroup } from "@angular/forms";

@Component({
  selector: 'app-config-fields',
  template: `
    <ng-container *ngFor="let item of dataOptions; trackBy: trackBy">
      <app-group-fields *ngIf="isPanel(item); else one" [panel]="item" [form]="form" [uniqId]="uniqId"></app-group-fields>
      <ng-template #one>
        <ng-container *ngIf="!item.hidden">
          <app-config-field-attribute-provider [form]="form" [options]="item" [uniqId]="uniqId">
            <app-field *configField [form]="form" [options]="item"></app-field>
          </app-config-field-attribute-provider>
        </ng-container>
      </ng-template>
    </ng-container>
  `
})
export class ConfigFieldsComponent extends BaseDirective {

  @Input() dataOptions: TFormOptions[] = [];
  @Input() form: FormGroup;
  @Input() uniqId: string;
  @Output()
  event = new EventEmitter<{ name: string; data?: any }>();

  rawConfig: IConfig;
  shapshot: any;
  isAdvanced = false;
  isCustomGroup = false;

  @Input()
  set model(data: IConfig) {
    if (!data) return;
    this.rawConfig = data;
    this.dataOptions = this.service.getPanels(data);
    this.service.getAttrs(data, this.dataOptions.map(a => a.name), this.dataOptions);
    this.form = this.service.toFormGroup(this.dataOptions);
    this.isCustomGroup = this.checkCustomGroup();
    this.isAdvanced = data.config.some((a) => a.ui_options && a.ui_options.advanced);
    this.shapshot = { ...this.form.value };
    this.event.emit({ name: 'load', data: { form: this.form } });
    this.stableView();
  }

  @ViewChildren(FieldComponent)
  fields: QueryList<FieldComponent>;

  @ViewChildren(GroupFieldsComponent)
  groups: QueryList<GroupFieldsComponent>;

  constructor(private service: FieldService,
              private fr: FullyRenderedService,
              private radio: ChannelService) {super();}

  get attr() {
    return this.dataOptions.filter((a) => a.type === 'group' && (a as IPanelOptions).activatable).reduce((p, c: IPanelOptions) => ({
      ...p,
      [c.name]: { active: c.active }
    }), {});
  }

  isPanel(item: TFormOptions) {
    return 'options' in item && !item.hidden;
  }

  trackBy(index: number, item: IPanelOptions): string {
    return item.name;
  }

  checkCustomGroup() {
    const check = (value) => {
      if (!value.hasOwnProperty('custom_group')) {
        return true;
      }

      return value.custom_group === true;
    }

    return this.dataOptions.some((config) => check(config));
  }

  /**
   * This method detects the moment rendering final of all fields and groups (with internal fields) on the page
   * it's need for test
   *
   * @member ConfigFieldsComponent
   */
  stableView() {
    this.fr.stableView(() => this.radio.next(keyChannelStrim.load_complete, 'Config has been loaded'));
  }
}
