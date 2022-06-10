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
import { Directive, EventEmitter, HostListener, Input, Output } from '@angular/core';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { DialogComponent } from '../dialog.component';
import { Upgrade } from "./upgrade.component";
import { concat, of } from "rxjs";
import { filter, map, switchMap, tap } from "rxjs/operators";
import { ApiService } from "@app/core/api";
import { EmmitRow } from "@app/core/types";
import { BaseDirective } from "../../directives";
import { IUpgrade, UpgradeMasterComponent as component } from "../upgrades/master/master.component";

export interface UpgradeParameters {
  cluster?: {
    id: number;
    hostcomponent: string;
  };
  upgrades: IUpgrade[];
}

@Directive({
  selector: '[appUpgrades]'
})
export class UpgradesDirective extends BaseDirective {
  @Input('appUpgrades') inputData: IUpgrade;
  @Output() refresh: EventEmitter<EmmitRow> = new EventEmitter<EmmitRow>();

  constructor(private api: ApiService, private dialog: MatDialog) {
    super();
  }

  @HostListener('click')
  onClick() {
    this.dialog.closeAll();
    this.prepare();
  }

  get hasConfig(): boolean {
    return this?.inputData?.config.config.length > 0
  }

  get hasHostComponent(): boolean {
    return this?.inputData?.hostcomponentmap.length > 0
  }

  get hasDisclaimer(): boolean {
    return !!this?.inputData?.ui_options['disclaimer']
  }

  prepare(): void {
    let dialogModel: MatDialogConfig
    const maxWidth = '1400px';
    const isMulty = this?.inputData.upgradable;
    const width = isMulty || this?.inputData.config?.config.length || this?.inputData.hostcomponentmap?.length ? '90%' : '400px';
    const title = this?.inputData.ui_options['disclaimer'] ? this?.inputData.ui_options['disclaimer'] : isMulty ? 'Run an actions?' : `Run an action [ ${this?.inputData.name} ]?`;
    const data: Upgrade = this.inputData as Upgrade;
    const model: UpgradeParameters = {
      cluster: {
        id: this.inputData.id,
        hostcomponent: this.inputData.url,
      },
      upgrades: [this.inputData]
    }

    dialogModel =  {
      width,
      maxWidth,
      data: {
        title,
        model,
        component,
      }
    };

    if (this.hasDisclaimer) {
      if (this.hasConfig || this.hasHostComponent) {
        this.runUpgrade(data, dialogModel);
      } else if (!this.hasConfig && !this.hasHostComponent) {
        this.runOldUpgrade(data, dialogModel);
      }
    } else {
      this.dialog.open(DialogComponent, dialogModel);
    }
  }

  runUpgrade(item: Upgrade, dialogModel: MatDialogConfig) {
    this.fork(item)
      .pipe(
        tap(text => {
            return this.dialog
              .open(DialogComponent, {
                data: {
                  title: 'Are you sure you want to upgrade?',
                  text: item.ui_options['disclaimer'] || text,
                  disabled: !item.upgradable,
                  controls: item.license === 'unaccepted' ? {
                    label: 'Do you accept the license agreement?',
                    buttons: ['Yes', 'No']
                  } : ['Yes', 'No']
                }
              })
              .afterClosed()
              .subscribe((res) => {
                if (res) this.dialog.open(DialogComponent, dialogModel);
              })
          }
        )
      ).subscribe();
  }

  runOldUpgrade(item: Upgrade, dialogModel: MatDialogConfig) {
    const license$ = item.license === 'unaccepted' ? this.api.put(`${item.license_url}accept/`, {}) : of();
    const do$ = this.api.post<{ id: number }>(item.do, {});

    this.fork(item)
      .pipe(
        switchMap(text =>
          this.dialog
            .open(DialogComponent, {
              data: {
                title: 'Are you sure you want to upgrade?',
                text: item.ui_options['disclaimer'] || text,
                disabled: !item.upgradable,
                controls: item.license === 'unaccepted' ? {
                  label: 'Do you accept the license agreement?',
                  buttons: ['Yes', 'No']
                } : ['Yes', 'No']
              }
            })
            .beforeClosed()
            .pipe(
              this.takeUntil(),
              filter(yes => yes),
              switchMap(() => concat(license$, do$))
            )
        )
      )
      .subscribe(row => this.refresh.emit({ cmd: 'refresh', row }));
  }

  fork(item: Upgrade) {
    const flag = item.license === 'unaccepted';
    return flag ? this.api.get<{ text: string }>(item.license_url).pipe(map(a => a.text)) : of(item.description);
  }
}
