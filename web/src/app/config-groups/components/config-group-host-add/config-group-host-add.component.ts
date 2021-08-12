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
import { SelectOption } from '../../../core/types';
import { Observable } from 'rxjs';

import { BaseFormDirective } from '../../../shared/add-component';
import { MatDialog } from '@angular/material/dialog';
import { ConfigGroupHostAddService } from '../../service/config-group-host-add.service';
import { ClusterService } from '../../../core/services/cluster.service';

@Component({
  selector: 'app-config-group-host-add',
  template: `
    <ng-container *ngIf="options$ | async as hosts">
      <mat-selection-list #listServices (selectionChange)="selectAll($event)">
        <mat-list-option *ngIf="hosts.length">All</mat-list-option>
        <mat-list-option *ngFor="let host of hosts" [value]="host">
          {{ host.name }}
        </mat-list-option>
      </mat-selection-list>
      <app-add-controls *ngIf="hosts.length; else not" [title]="'Add'" [disabled]="!form.valid" (cancel)="onCancel()"
                        (save)="save()"></app-add-controls>
    </ng-container>
    <ng-template #not>
      <p>
        <i>
          There are no new hosts. You config group already has all of them.
        </i>
      </p>
    </ng-template>
  `
})
export class AddHostToConfigGroupComponent extends BaseFormDirective implements OnInit {
  options$: Observable<SelectOption[]>;
  @ViewChild('listServices')
  private listServices: MatSelectionList;

  constructor(service: ConfigGroupHostAddService, dialog: MatDialog, private cluster: ClusterService) {
    super(service, dialog);
  }

  ngOnInit(): void {
    const { typeName } = this.cluster.Current;
    this.options$ = this.service.getList(typeName, {});
  }

  selectAll(e: MatSelectionListChange): void {
    if (!e.option.value) {
      if (e.option.selected) this.listServices.selectAll();
      else this.listServices.deselectAll();
    }
  }

  save(): void {
    const groupId = this.service.Current.id;
    const result = this.listServices.selectedOptions.selected.filter(a => a.value).map(a => ({
      host: +a.value.id,
      group: groupId
    }));

    this.service
      .add(result)
      .pipe(this.takeUntil())
      .subscribe(() => this.dialog.closeAll());
  }
}
