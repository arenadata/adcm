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
import { Observable } from 'rxjs';
import { BaseFormDirective } from './base-form.directive';
import { take } from "rxjs/operators";

@Component({
  selector: 'app-add-service',
  template: `
    <ng-container *ngIf="options$ | async as protos">
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
  options$: Observable<SelectOption[]>;
  @ViewChild('listServices')
  private listServices: MatSelectionList;

  ngOnInit() {
    this.options$ = this.service.getProtoServiceForCurrentCluster();
  }


  selectAll(e: MatSelectionListChange) {
    if (!e.option.value) {
      if (e.option.selected) this.listServices.selectAll();
      else this.listServices.deselectAll();
    }
  }

  save() {
    const result = this.listServices.selectedOptions.selected.filter(a => a.value).map(a => ({
      prototype_id: +a.value.id,
      service_name: a.value.name,
      license: a.value.license,
      license_url: a.value.license_url,
    }));
    this.service
      .addService(result)
      .pipe(this.takeUntil())
      .subscribe(() => this.dialog.closeAll());
  }
}
