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
import { Component, Input, OnInit } from '@angular/core';
import { IAction } from '@app/core/types';

import { ActionsService } from '../actions.service';
import { mapTo, map } from 'rxjs/operators';

const fruit = {
  display_name: 'Fruit',
  desctiption: 'fruit description',
  children: [
    { display_name: 'Apple', description: 'description or some description about this action description or some description about this action' },
    { display_name: 'Banana', description: 'description or some description about this action bannana' },
    { display_name: 'Fruit loops', description: '' },
  ],
};

const vegetable = {
  display_name: 'Vegetables',
  desctiption: 'description or some description about this action some description about this action Vegetables',
  children: [
    {
      display_name: 'Green',
      description: 'description or some description about this action description or some description about this action',
      children: [
        { display_name: 'Broccoli', description: 'description or some description about this action description or some description about this action' },
        { display_name: 'Brussels sprouts', description: 'description or some description about this action bannana' },
      ],
    },
    {
      display_name: 'Orange',
      description: 'description or some description about this action bannana',
      children: [
        { display_name: 'Pumpkins', description: 'description or some description about this action description or some description about this action' },
        { display_name: 'Carrots', description: 'description or some description about this action bannana' },
      ],
    },
  ],
};

@Component({
  selector: 'app-action-list',
  template: `
    <button color="accent" [disabled]="disabled" mat-icon-button [matMenuTriggerFor]="panel.menu" (click)="getData()" matTooltip="Choose action">
      <mat-icon>play_circle_outline</mat-icon>
    </button>
    <app-menu-item #panel [items]="actions" [cluster]="cluster"></app-menu-item>
  `,
})
export class ActionListComponent {
  @Input() cluster: { id: number; hostcomponent: string; action: string };
  @Input() disabled: boolean;
  @Input() actions: any;
  constructor(private service: ActionsService) {}

  getData(): void {
    if (!this.actions?.length)
      this.service
        .getActions(this.cluster.action)
        .pipe(map((a) => [fruit, vegetable, ...a]))
        .subscribe((a) => (this.actions = a));
  }
}
