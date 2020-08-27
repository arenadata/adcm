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
import { Component, Input } from '@angular/core';

import { ActionsService } from '../actions.service';

@Component({
  selector: 'app-action-list',
  template: `
    <button *ngIf="!asButton; else btn" mat-icon-button color="accent" [disabled]="disabled" [matMenuTriggerFor]="panel.menu" (click)="getData()" matTooltip="Choose action">
      <mat-icon>play_circle_outline</mat-icon>
    </button>
    <ng-template #btn>
      <button mat-raised-button color="warn" [disabled]="disabled" [matMenuTriggerFor]="panel.menu" (click)="getData()">
        <span>Run action</span>&nbsp;<mat-icon>add_task</mat-icon>
      </button>
    </ng-template>
    <app-menu-item #panel [items]="actions" [cluster]="cluster"></app-menu-item>
  `,
})
export class ActionListComponent {
  @Input() cluster: { id: number; hostcomponent: string; action: string };
  @Input() disabled: boolean;
  @Input() actions: any;
  @Input() asButton = false;

  constructor(private service: ActionsService) {}

  getData(): void {
    if (!this.actions?.length) this.service.getActions(this.cluster.action).subscribe((a) => (this.actions = a));
  }
}
