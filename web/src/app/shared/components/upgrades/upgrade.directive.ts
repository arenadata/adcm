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
import { IUpgrade } from "./upgrade.component";
import {combineLatest, concat, Observable, of} from "rxjs";
import { filter, map, switchMap, tap } from "rxjs/operators";
import { ApiService } from "@app/core/api";
import { EmmitRow, Entities } from "@app/core/types";
import { BaseDirective } from "../../directives";
import { UpgradeMasterComponent as component } from "../upgrades/master/master.component";
import { AddService } from "@app/shared/add-component/add.service";
import { IRawHosComponent } from "@app/shared/host-components-map/types";
import { ListResult } from "@app/models/list-result";
import {ClusterService} from "@app/core/services/cluster.service";
import {ICluster} from "@app/models/cluster";
import {ServiceService} from "@app/services/service.service";

export interface UpgradeParameters {
  cluster?: {
    id: number;
    hostcomponent: IRawHosComponent;
  };
  upgrades: IUpgrade[];
}

@Directive({
  selector: '[appUpgrades]'
})
export class UpgradesDirective extends BaseDirective {
  @Input('appUpgrades') inputData: IUpgrade;
  @Input() clusterId: number;
  @Input() bundleId: number;
  @Output() refresh: EventEmitter<EmmitRow> = new EventEmitter<EmmitRow>();

  hc: IRawHosComponent;
  needPrototype = false;
  needLicenseAcceptance: [];


  constructor(private api: ApiService,
              private dialog: MatDialog,
              private add: AddService,
              private service: ServiceService,
              private cluster: ClusterService) {
    super();
  }

  @HostListener('click')
  onClick() {
    this.dialog.closeAll();
    this.checkServicesAndPrepare();
  }

  get hasConfig(): boolean {
    return this?.inputData?.config?.config?.length > 0
  }

  get hasHostComponent(): boolean {
    return this?.inputData?.hostcomponentmap?.length > 0
  }

  get hasDisclaimer(): boolean {
    return !!this?.inputData?.ui_options['disclaimer']
  }

  prepare(): void {
    let dialogModel: MatDialogConfig
    const maxWidth = '1400px';
    const isMulty = this?.inputData.upgradable;
    const width = isMulty || this.hasConfig || this.hasHostComponent ? '90%' : '400px';
    const title = this?.inputData.ui_options['disclaimer'] ? this?.inputData.ui_options['disclaimer'] : isMulty ? 'Run upgrades?' : `Run upgrade [ ${this?.inputData.name} ]?`;
    const data: IUpgrade = this.inputData as IUpgrade;
    const model: UpgradeParameters = {
      cluster: {
        id: this.clusterId,
        hostcomponent: this.hc,
      },
      upgrades: [this.inputData],
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
        this.runOldUpgrade(data);
      }
    } else {
      if (!this.hasConfig && !this.hasHostComponent) {
        dialogModel.maxWidth = '1400px';
        dialogModel.width = '400px';
        dialogModel.minHeight = '180px';
        dialogModel.data.title = 'Are you sure you want to upgrade?'
        dialogModel.data.text = 'The cluster will be prepared for upgrade';
      }

      if (this.needLicenseAcceptance.length > 0) {
        combineLatest(this.needLicenseAcceptance.map((o) => {
          this.service.acceptServiceLicense(o).pipe(
            tap(() => {
                this.dialog.open(DialogComponent, dialogModel);
              }
            )).subscribe();
        }));
      } else {
        this.dialog.open(DialogComponent, dialogModel);
      }

    }
  }

  runUpgrade(item: IUpgrade, dialogModel: MatDialogConfig) {
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
              .pipe(
                filter(yes => yes)
              )
              .subscribe(() => {
                if (this.needLicenseAcceptance.length > 0) {
                  combineLatest(this.needLicenseAcceptance.map((o) => {
                    this.service.acceptServiceLicense(o).pipe(
                      tap(() => {
                          this.dialog.open(DialogComponent, dialogModel);
                        }
                      )).subscribe();
                  }));
                } else {
                  this.dialog.open(DialogComponent, dialogModel);
                }
              })

          }
        )
      ).subscribe();
  }

  runOldUpgrade(item: IUpgrade) {
    const license$ = item.license === 'unaccepted' ? this.api.put(`${item.license_url}accept/`, {}) : of();
    const do$ = this.api.post<{ id: number }>(item.do, {});

    this.fork(item)
      .pipe(
        tap(text =>
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
            .afterClosed()
            .pipe(
              filter(yes => yes),
              switchMap(() => concat(license$, do$))
            )
            .subscribe((row) => {
              if (this.needLicenseAcceptance.length > 0) {
                combineLatest(this.needLicenseAcceptance.map((o) => {
                  this.service.acceptServiceLicense(o).subscribe(() => this.refresh.emit({cmd: 'refresh', row}));
                }));
              } else {
                this.refresh.emit({cmd: 'refresh', row});
              }
            })
        )
      )
      .subscribe();
  }

  fork(item: IUpgrade) {
    const flag = item.license === 'unaccepted';
    return flag ? this.api.get<{ text: string }>(item.license_url).pipe(map(a => a.text)) : of(item.description);
  }

  checkServicesAndPrepare() {
    let oldVersionAcceptedServices;

    if (!this.add.Cluster) {
      this.getCluster().pipe(
        tap((res: ICluster) => this.cluster.Cluster = res)
      ).subscribe();
    }

      this.getClusterServices().subscribe(res => {
        oldVersionAcceptedServices = res.map(service => service.name);

        this.getPrototypeServices().subscribe(res => {
          this.needLicenseAcceptance = res.results
              .filter((service) => service.bundle_id === this.inputData.bundle_id && oldVersionAcceptedServices.includes(service.name) && service.license === 'unaccepted')
              .map((i) => ({
                  prototype_id: i.id,
                  service_name: i.name,
                  license: i.license,
                  license_url: i.license_url,
              }));

          if (this.hasHostComponent) {
            this.checkHostComponents();
          } else {
            this.prepare();
          }
        })
      })
  }

  checkHostComponents() {
    this.getClusterInfo()
      .pipe(
        tap((cluster): any => {
          const hostComponentMap = this.inputData.hostcomponentmap;

          hostComponentMap.forEach((hc, index) => {
            if (!cluster.component.find(c => c.name === hc.component)) {
              this.needPrototype = true;
              const params = {
                bundle_id: this.inputData.bundle_id,
                type: 'component',
                name: hc.component,
                parent_name: hc.service,
                limit: 50,
                offset: 0
              };

              // fix later
              this.add.getPrototype('prototype', params).subscribe((prototype): any => {
                if (prototype[0]) {
                  cluster.component.push(prototype[0]);
                  this.hc = cluster;
                }

                if (hostComponentMap.length === index + 1) {
                  if (!this.hc) this.hc = cluster;
                  this.prepare();
                }
              })
            }
          })

          if (!this.needPrototype) {
            this.hc = cluster;
            this.prepare();
          }
        }),
      ).subscribe();
  }

  getCluster(): Observable<any> {
    return this.api.get(`api/v1/cluster/${this.clusterId}/`);
  }

  getClusterInfo(): Observable<any> {
    return this.api.get(`api/v1/cluster/${this.clusterId}/hostcomponent/`);
  }

  getPrototype(params): Observable<any> {
    return this.add.getPrototype('prototype', params);
  }

  getClusterServices(): Observable<any> {
    return this.api.get<ListResult<Entities>>(`api/v1/cluster/${this.clusterId}/service/`);
  }

  getPrototypeServices(): Observable<any> {
    return this.api.get<ListResult<Entities>>('/api/v1/stack/service/');
  }
}
