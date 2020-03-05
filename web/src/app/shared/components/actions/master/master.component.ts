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
import { AfterViewInit, Component, EventEmitter, OnInit, ViewChild } from '@angular/core';
import { ApiService } from '@app/core/api';
import { IAction } from '@app/core/types';
import { FieldService } from '@app/shared/configuration/field.service';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';
import { ServiceHostComponent } from '@app/shared/host-components-map/services2hosts/service-host.component';

import { ConfigFieldsComponent } from '../../../configuration/fields/fields.component';
import { BaseDirective } from '../../../directives/base.directive';
import { ActionParameters } from '../actions.directive';

@Component({
  selector: 'app-master',
  templateUrl: './master.component.html',
  styleUrls: ['./master.component.scss']
})
export class ActionMasterComponent extends BaseDirective implements DynamicComponent, OnInit, AfterViewInit {
  event: EventEmitter<DynamicEvent> = new EventEmitter();
  model: ActionParameters;
  action: IAction;

  isHmcRequired = false;
  isConfig = false;

  @ViewChild('fields') fields: ConfigFieldsComponent;

  isAdvanced = false;
  set advanced(value: boolean) {
    this.config.filterApply(this.fields.dataOptions, { advanced: value, search: '' });
  }

  arh: { parent: HTMLElement; holder: HTMLElement };

  constructor(private api: ApiService, private config: FieldService) {
    super();
  }

  ngOnInit(): void {
    if (this.model && this.model.actions.length === 1) {
      this.choose(this.model.actions[0]);
    }
  }

  ngAfterViewInit(): void {
    if (this.isConfig && this.fields) {
      setTimeout(() => this.isAdvanced = this.fields.rawConfig.config.some(a => a.ui_options && a.ui_options.advanced));
    }
  }

  choose(action: IAction) {
    this.action = action;
    this.isConfig = !!(this.action.config && this.action.config.config.length);
    this.isHmcRequired = !!this.action.hostcomponentmap;
  }

  run(value: { config: ConfigFieldsComponent; hostmap: ServiceHostComponent }) {
    const data: any = {};
    if (value.config) data.value = value.config.form;
    if (value.hostmap) data.hostmap = value.hostmap.service.statePost.data;

    const request$ =
      !this.isConfig && !this.isHmcRequired
        ? this.api.post(this.action.run, {})
        : this.api.post(this.action.run, {
            config: data.value ? this.config.parseValue(data.value, this.action.config.config) : {},
            hc: data.hostmap
          });

    request$.pipe(this.takeUntil()).subscribe(() => this.cancel());
  }

  cancel() {
    this.event.emit({ name: 'cancel' });
  }
}
