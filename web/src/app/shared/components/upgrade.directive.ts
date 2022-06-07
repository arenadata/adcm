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
import {Directive, EventEmitter, HostListener, Input, Output} from '@angular/core';
import { MatDialog, MatDialogConfig } from '@angular/material/dialog';
import { DialogComponent } from './dialog.component';
import { Upgrade } from "@app/shared/components/upgrade.component";
import { concat, of } from "rxjs";
import { filter, map, switchMap } from "rxjs/operators";
import { ApiService } from "@app/core/api";
import { EmmitRow } from "@app/core/types";

@Directive({
  selector: '[appUpgrades]'
})
export class UpgradesDirective {
  @Input('appUpgrades') inputData: Upgrade;
  @Output() refresh: EventEmitter<EmmitRow> = new EventEmitter<EmmitRow>();

  constructor(private api: ApiService, private dialog: MatDialog) {}

  @HostListener('click')
  onClick() {
    this.dialog.closeAll();
    const dialogModel: MatDialogConfig = this.prepare();
    this.dialog.open(DialogComponent, dialogModel);
  }

  prepare(): MatDialogConfig {
    const maxWidth = '1400px';
    const model = this.inputData;

    if (model.ui_options?.disclaimer) {
      if (model.config.config.length === 0
        && model.hostcomponentmap.length === 0) return { data: { title: 'No parameters for run the action', model: null, component: null } };

      if (model.config.config.length > 0
        && model.hostcomponentmap.length > 0) return { data: { title: 'No parameters for run the action', model: null, component: null } };

      if (model.config.config.length > 0
        && model.hostcomponentmap.length === 0) return { data: { title: 'No parameters for run the action', model: null, component: null } };

      if (model.config.config.length === 0
        && model.hostcomponentmap.length > 0) return { data: { title: 'No parameters for run the action', model: null, component: null } };
    } else {
      if (model.config.config.length === 0
        && model.hostcomponentmap.length === 0) return { data: { title: 'No parameters for run the action', model: null, component: null } };

      if (model.config.config.length > 0
        && model.hostcomponentmap.length > 0) return { data: { title: 'No parameters for run the action', model: null, component: null } };

      if (model.config.config.length > 0
        && model.hostcomponentmap.length === 0) return { data: { title: 'No parameters for run the action', model: null, component: null } };

      if (model.config.config.length === 0
        && model.hostcomponentmap.length > 0) return { data: { title: 'No parameters for run the action', model: null, component: null } };
    }

    // const act = model.actions[0];
    // const isMulty = model.actions.length > 1;
    //
    // const width = isMulty || act.config?.config.length || act.hostcomponentmap?.length ? '90%' : '400px';
    // const title = act.ui_options?.disclaimer ? act.ui_options.disclaimer : isMulty ? 'Run an actions?' : `Run an action [ ${act.display_name} ]?`;
    //
    // return {
    //   width,
    //   maxWidth,
    //   data: {
    //     title,
    //     model,
    //     component,
    //   }
    // };
  }

  runUpgrade(item: Upgrade) {
    const license$ = item.license === 'unaccepted' ? this.api.put(`${item.license_url}accept/`, {}) : of();
    const do$ = this.api.post<{ id: number }>(item.do, {});
    this.fork(item)
      .pipe(
        switchMap(text =>
          this.dialog
            .open(DialogComponent, {
              data: {
                title: 'Are you sure you want to upgrade?',
                text,
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
