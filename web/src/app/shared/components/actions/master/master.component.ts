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
import { ChangeDetectionStrategy, Component, EventEmitter, OnInit } from '@angular/core';
import { IAction } from '@app/core/types';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';

import { BaseDirective } from '../../../directives/base.directive';
import { ActionParameters } from '../actions.directive';
import { IValue, MasterService, whatShow } from './master.service';

@Component({
  selector: 'app-master',
  templateUrl: './master.component.html',
  styles: [
    `
      .action-button {
        background: none !important;
        margin: 6px 0;

        &:hover {
          background: rgba(255, 255, 255, 0.04) !important;
        }
      }
    `
  ],
  providers: [MasterService],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ActionMasterComponent extends BaseDirective implements DynamicComponent, OnInit {
  event: EventEmitter<DynamicEvent> = new EventEmitter();
  model: ActionParameters; // = { actions: [], cluster: null };

  action: IAction;
  show: whatShow;

  constructor(private service: MasterService) {
    super();
  }

  ngOnInit(): void {
    if (this.model.actions.length === 1) this.choose(this.model.actions[0]);
  }

  choose(action: IAction) {
    this.action = action;
    this.show = this.service.spotShow(action);
  }

  run(value: IValue) {
    this.service
      .send(value, this.action.run, this.show === 'none', this.action.config.config)
      .pipe(this.takeUntil())
      .subscribe(() => this.cancel());
  }

  cancel() {
    this.event.emit({ name: 'cancel' });
  }
}
