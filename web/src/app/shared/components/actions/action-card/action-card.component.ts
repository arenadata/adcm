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
import { EventMessage, SocketState } from '@app/core/store';
import { Cluster, Entities, isIssue } from '@app/core/types';
import { SocketListenerDirective } from '@app/shared/directives';
import { Store } from '@ngrx/store';
import { Observable, of } from 'rxjs';

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
export class ActionCardComponent extends SocketListenerDirective implements OnInit {
  model: Entities;
  actions$: Observable<any[]> = of([]);

  constructor(private details: ClusterService, private service: ActionsService, socket: Store<SocketState>) {
    super(socket);
  }

  ngOnInit(): void {
    if (!isIssue(this.details.Current.issue))
      this.actions$ = this.service.getActions(this.details.Current.action);
    super.startListenSocket();
  }

  socketListener(m: EventMessage) {
    if (this.details.Current?.typeName === m.object.type && this.details.Current?.id === m.object.id && (m.event === 'change_state' || m.event === 'clear_issue')) {
      this.actions$ = this.service.getActions(this.details.Current.action);
    }
  }

  get clusterData() {
    const { id, hostcomponent } = this.details.Cluster || (this.details.Current as Cluster);
    return { id, hostcomponent };
  }
}
