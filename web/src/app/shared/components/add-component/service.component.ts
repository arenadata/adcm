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
import { MatSelectionList } from '@angular/material/list';
import { SelectOption } from '@app/core/types';
import { Observable } from 'rxjs';

import { BaseFormDirective } from './base-form.directive';

@Component({
  selector: 'app-add-service',
  template: `
    <ng-container *ngIf="options$ | async as protos">
      <mat-selection-list #listServices class="add-service">
        <mat-list-option *ngFor="let proto of protos" [value]="proto">
          {{ proto.name }}
        </mat-list-option>
      </mat-selection-list>
      <p class="controls" *ngIf="protos.length; else not">
        <button mat-raised-button color="accent" (click)="save()">Save</button>
        <button mat-raised-button color="primary" (click)="onCancel()">Cancel</button>
      </p>
    </ng-container>
    <ng-template #not>
      <p>
        <i>
          There are no new services. You cluster already has all of them.
          </i>
      </p>
    </ng-template>
  `,
})
export class ServiceComponent extends BaseFormDirective implements OnInit {
  options$: Observable<SelectOption[]>;
  @ViewChild('listServices', { static: false })
  private listServices: MatSelectionList;

  ngOnInit() {
    this.options$ = this.service.getProtoServiceForCurrentCluster();
  }

  save() {
    const result = this.listServices.selectedOptions.selected.map(a => ({ prototype_id: +a.value.id }));
    this.service
      .addService(result)
      .pipe(this.takeUntil())
      .subscribe(() => this.onCancel());
  }
}
