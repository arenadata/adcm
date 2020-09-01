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
import { Component, OnInit } from '@angular/core';
import { ClusterService } from '@app/core';
import { Cluster, Entities } from '@app/core/types';
import { Observable } from 'rxjs';

import { ActionsService } from '../actions.service';

@Component({
  selector: 'app-action-card',
  template: `
    <ng-container *ngIf="actions$ | async as actions">
      <p *ngIf="!actions.length">Nothing to display.</p>
      <app-card-item [items]="actions" [cluster]="clusterData"></app-card-item>
    </ng-container>
  `, 
})
export class ActionCardComponent implements OnInit {
  model: Entities;
  actions$: Observable<any[]>;

  constructor(private details: ClusterService, private service: ActionsService) {}

  ngOnInit(): void {
    this.actions$ = this.service.getActions(this.details.Current.action);
  }

  get clusterData() {
    const { id, hostcomponent } = this.details.Cluster || (this.details.Current as Cluster);
    return { id, hostcomponent };
  }
}
