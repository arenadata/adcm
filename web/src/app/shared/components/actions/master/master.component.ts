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
import { Component, ElementRef, EventEmitter, OnInit, ViewChild } from '@angular/core';
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
    `,
  ],
  providers: [MasterService],
})
export class ActionMasterComponent extends BaseDirective implements DynamicComponent, OnInit {
  event: EventEmitter<DynamicEvent> = new EventEmitter();
  model: ActionParameters;
  action: IAction;
  show: whatShow;

  @ViewChild('runBtn', { read: ElementRef }) runBtn: ElementRef;

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

  isDisabled(value: IValue) {
    return value && ((value.hostmap && value.hostmap.noValid) || (value.config && !value.config.form?.valid));
  }

  run(value: IValue = {}) {
    const data = this.service.parseData(value);
    this.service
      .send(this.action.run, data)
      .pipe(this.takeUntil())
      .subscribe(() => this.cancel());
  }

  onEnterKey() {
    this.runBtn.nativeElement.click();
  }

  cancel() {
    this.event.emit({ name: 'cancel' });
  }
}
