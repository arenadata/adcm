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
import { Component, Input, QueryList, ViewChildren } from '@angular/core';

import { ChannelService, FullyRenderedService, keyChannelStrim } from '@app/core/services';
import { FieldService, TFormOptions } from '../services/field.service';
import { FieldComponent } from '../field/field.component';
import { GroupFieldsComponent } from '../group-fields/group-fields.component';
import { IConfig, IPanelOptions } from '../types';
import { BaseDirective } from '@adwp-ui/widgets';
import { MainService } from '@app/shared/configuration/main/main.service';
import { FormGroup } from '@angular/forms';

@Component({
  selector: 'app-config-fields',
  template: `
    <ng-container *ngFor="let item of dataOptions; trackBy: trackBy">
      <app-group-fields *ngIf="isPanel(item); else one" [panel]="item" [form]="form"
                        [groupForm]="groupsForm"></app-group-fields>
      <ng-template #one>
        <div class="row d-flex">
          <div class="group-checkbox d-flex" style="padding: 5px">
            <ng-container *ngIf="item.configGroup as ConfigGroupControl">
              <mat-checkbox [formControl]="ConfigGroupControl"></mat-checkbox>
            </ng-container>
          </div>
          <app-field class="w100" *ngIf="!item.hidden" [form]="form" [options]="item"
                     [ngClass]="{ 'read-only': item.read_only }"></app-field>
        </div>
      </ng-template>
    </ng-container>
  `,
  styles: [`.group-checkbox {
    justify-content: center;
    align-items: center
  }`]
})
export class ConfigFieldsComponent extends BaseDirective {

  @Input() dataOptions: TFormOptions[] = [];
  @Input() form = this.service.toFormGroup();
  @Input() groupsForm: FormGroup;
  rawConfig: IConfig;
  shapshot: any;
  isAdvanced = false;


  @Input()
  set model(data: IConfig) {
    if (!data) return;
    this.rawConfig = data;
    this.groupsForm = this.service.toGroupsFormGroup(data.attr.group_keys);
    this.dataOptions = this.service.getPanels(data, this.groupsForm);
    this.form = this.service.toFormGroup(this.dataOptions);
    this.isAdvanced = data.config.some((a) => a.ui_options && a.ui_options.advanced);
    this.shapshot = { ...this.form.value };
    this.main.events.isLoaded();
    this.stableView();
  }

  @ViewChildren(FieldComponent)
  fields: QueryList<FieldComponent>;

  @ViewChildren(GroupFieldsComponent)
  groups: QueryList<GroupFieldsComponent>;

  constructor(private service: FieldService,
              private fr: FullyRenderedService,
              private radio: ChannelService,
              private main: MainService) {super();}

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

  onToggleCheckbox;

  /**
   * This method detects the moment rendering final of all fields and groups (with internal fields) on the page
   * it's need for test
   *
   * @memberof ConfigFieldsComponent
   */
  stableView() {
    this.fr.stableView(() => this.radio.next(keyChannelStrim.load_complete, 'Config has been loaded'));
  }
}
