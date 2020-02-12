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
import { Component, EventEmitter, OnInit } from '@angular/core';
import { ApiService } from '@app/core/api';
import { IAction, parseValueConfig } from '@app/core/types';

import { ConfigFieldsComponent } from '../../../configuration/fields/fields.component';
import { BaseDirective } from '../../../directives/base.directive';
import { ActionParameters } from '../actions.directive';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';
import { ServiceHostComponent } from '@app/shared/host-components-map/services2hosts/service-host.component';

@Component({
  selector: 'app-master',
  templateUrl: './master.component.html',
  styleUrls: ['./master.component.scss'],
})
export class ActionMasterComponent extends BaseDirective implements DynamicComponent, OnInit {
  event: EventEmitter<DynamicEvent> = new EventEmitter();
  model: ActionParameters;
  action: IAction;

  isHmcRequired = false;
  isConfig = false;

  arh: { parent: HTMLElement; holder: HTMLElement };

  constructor(private api: ApiService) {
    super();
  }

  ngOnInit(): void {
    if (this.model && this.model.actions.length === 1) {
      this.choose(this.model.actions[0]);
    }
  }

  choose(action: IAction) {
    this.action = action;
    this.isConfig = !!(this.action.config && this.action.config.config.length);
    this.isHmcRequired = !!this.action.hostcomponentmap;
  }

  run(config: ConfigFieldsComponent, hostmap: ServiceHostComponent) {
    const data: any = {};
    if (config) data.value = config.form.value;
    if (hostmap) data.hostmap = hostmap.service.statePost.data;

    const request$ =
      !this.isConfig && !this.isHmcRequired
        ? this.api.post(this.action.run, {})
        : this.api.post(this.action.run, {
            config: parseValueConfig(this.action.config.config, data.value),
            hc: data.hostmap,
          });

    request$.pipe(this.takeUntil()).subscribe(() => this.cancel());
  }

  cancel() {
    this.event.emit({ name: 'cancel' });
  }
}
