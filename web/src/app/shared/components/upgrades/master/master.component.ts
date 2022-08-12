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
import {
  AfterViewChecked,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  OnInit,
  ViewChild
} from '@angular/core';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic/dynamic.directive';
import { BaseDirective } from '@app/shared/directives';
import { IMasterData, IValue, MasterService, whatShow } from './master.service';
import { IUpgrade } from "@app/shared/components";
import { UpgradeParameters } from "@app/shared/components/upgrades/upgrade.directive";
import { MatStepper } from "@angular/material/stepper";
import {ChangeDetection} from "@angular/cli/lib/config/schema";

@Component({
  selector: 'app-master',
  templateUrl: './master.component.html',
  styleUrls: ['./master.component.scss'],
  providers: [MasterService],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UpgradeMasterComponent extends BaseDirective implements DynamicComponent, OnInit, AfterViewChecked {
  event: EventEmitter<DynamicEvent> = new EventEmitter();
  model: UpgradeParameters;
  upgrade: IUpgrade;
  show: whatShow;

  verbose = false;

  @ViewChild('runBtn', { read: ElementRef }) runBtn: ElementRef;

  constructor(private service: MasterService, public cd: ChangeDetectorRef) {
    super();
  }

  ngOnInit(): void {
    if (this.model.upgrades?.length === 1) this.choose(this.model.upgrades[0]);
  }

  ngAfterViewChecked() {
    this.cd.detectChanges();
  }

  choose(upgrade: IUpgrade) {
    this.upgrade = upgrade;
    this.show = this.service.spotShow(upgrade);
  }

  isDisabled(value: IValue) {
    return value && ((value.hostmap && value.hostmap.noValid) || (value.config && !value.config.form?.valid));
  }

  hmStepValid(hostmap) {
    return hostmap && hostmap?.noValid;
  }

  configStepValid(config) {
    return config && !config?.form?.valid;
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

  back(stepper: MatStepper) {
    stepper.previous();
  }

  needMargin() {
    return !(this?.model?.upgrades[0]?.config?.config?.length > 0 && this?.model?.upgrades[0]?.hostcomponentmap?.length > 0);
  }
}
