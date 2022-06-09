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
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic/dynamic.directive';
import { BaseDirective } from '@app/shared/directives';
import { UpgradesDirective} from "@app/shared/components/upgrades/upgrade.directive";
import { IMasterData, IValue, MasterService, whatShow } from './master.service';
import { IConfig } from "@app/shared/configuration/types";
import { HostComponent, IUIOptions } from "@app/core/types";

export interface IUpgrade {
  bundle_id: number;
  config: IConfig;
  description: string;
  do: string;
  from_edition: string[];
  hostcomponentmap: HostComponent[];
  id: number;
  license: string;
  license_url: string;
  max_strict: boolean;
  max_version: string;
  min_strict: boolean;
  min_version: string;
  name: string;
  state_available: string;
  state_on_success: string;
  ui_options: IUIOptions[];
  upgradable: boolean;
  url: string;
}

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

      .controls-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
    `,
  ],
  providers: [MasterService],
})
export class UpgradeMasterComponent extends BaseDirective implements DynamicComponent, OnInit {
  event: EventEmitter<DynamicEvent> = new EventEmitter();
  model: /*UpgradeParameters*/any;
  upgrade: IUpgrade;
  show: whatShow;

  verbose = false;

  @ViewChild('runBtn', { read: ElementRef }) runBtn: ElementRef;

  constructor(private service: MasterService) {
    super();
  }

  ngOnInit(): void {
    if (this.model.actions.length === 1) this.choose(this.model.actions[0]);
  }

  choose(upgrade: IUpgrade) {
    this.upgrade = upgrade;
    this.show = this.service.spotShow(upgrade);
  }

  isDisabled(value: IValue) {
    return value && ((value.hostmap && value.hostmap.noValid) || (value.config && !value.config.form?.valid));
  }

  run(value: IValue = {}) {
    const data: IMasterData = this.service.parseData(value);
    if (data) {
      data.verbose = this.verbose;
    }
    this.service
      .send(this.upgrade.do, data)
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
