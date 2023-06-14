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
import { Component, OnInit, ViewChild } from '@angular/core';
import { MatSelectionList, MatSelectionListChange } from '@angular/material/list';
import { SelectOption } from '@app/core/types';
import { Observable, of } from 'rxjs';
import { BaseFormDirective } from './base-form.directive';
import { filter, finalize, switchMap } from "rxjs/operators";
import { DialogComponent } from '../components/dialog.component';
import { DependenciesComponent } from '../host-components-map/dependencies.component';

@Component({
  selector: 'app-add-service',
  template: `
    <ng-container *ngIf="options as protos">
      <mat-selection-list #listServices (selectionChange)="selectAll($event)">
        <mat-list-option *ngIf="protos.length">All</mat-list-option>
        <mat-list-option *ngFor="let proto of protos" [value]="proto">
          {{ proto.name }}
        </mat-list-option>
      </mat-selection-list>
      <app-add-controls *ngIf="protos.length; else not" [title]="'Add'" [disabled]="!form.valid" (cancel)="onCancel()" (save)="save()"></app-add-controls>
    </ng-container>
    <ng-template #not>
      <p>
        <i>
          There are no new services. Your cluster already has all of them.
        </i>
      </p>
    </ng-template>
  `
})
export class ServiceComponent extends BaseFormDirective implements OnInit {
  options: SelectOption[];
  addedServices: any[] = [];
  addedRequires: any[] = [];

  @ViewChild('listServices')
  private listServices: MatSelectionList;

  ngOnInit() {
    this.service.getProtoServiceForCurrentCluster()
      .subscribe((options) => {
        this.options = options
      });
  }


  selectAll(e: MatSelectionListChange) {
    if (!e.option.value) {
      if (e.option.selected) this.listServices.selectAll();
      else this.listServices.deselectAll();
    }
  }

  addServiceToList(services, unshift?: boolean) {
    if (!services?.length || services?.length === 0) return;

    services.forEach((service) => {
      const selectedService = this.options.filter((option: any) => option?.id === service)[0] as any;

      if (!selectedService) return;

      if (unshift) {
        if (!this.addedRequires?.find((options) => selectedService?.id === options?.id)) {
          this.addedRequires.unshift(selectedService);
        }
      } else {
        if (!this.addedServices?.find((options) => selectedService?.id === options?.id)) {
          this.addedServices.push(selectedService);
        }
      }

      if (selectedService?.requires?.length > 0) {
        this.addServiceToList(selectedService.requires.map((require) => require.prototype_id), true);
      }
    })

  }

  buildServicesList() {
    const selected = this.listServices.selectedOptions.selected.filter(a => a.value).map((service) => service.value.id);

    this.addServiceToList(selected);

    this.addedRequires = this.addedRequires.filter((service) => {
      return !this.addedServices.includes(service);
    } );

    return selected;
  }

  requestApprove(requires) {
    if (requires.length === 0) return of(true);

    return this.dialog
      .open(DialogComponent, {
        data: {
          title: 'This service cannot be added without the following dependencies.',
          component: DependenciesComponent,
          model: requires.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true })),
          controls: ['Add All', 'Cancel'],
        },
      })
      .beforeClosed()
      .pipe(
        filter((a) => a),
        switchMap(() =>{
          return of(true)
        })
      )
  }

  save() {
    const selectedServices = this.buildServicesList();

    if (selectedServices.length === 0) {
      this.dialog.closeAll();
      return;
    }

    const result = [...this.addedRequires, ...this.addedServices]?.map((options) => ({
      prototype_id: +options.id,
      service_name: options.name,
      license: options.license,
      license_url: options.license_url,
    }))

    this.requestApprove(this.addedRequires)
      .pipe(
        finalize(() => {
          this.addedServices = this.addedServices.filter((service) => service.prototype_id);
          this.addedRequires = []
        })
      )
      .subscribe(() => {
        this.service
        .addServiceInCluster(result)
        .pipe(
          finalize(() => this.dialog.closeAll()))
        .subscribe();
      })
  }
}
