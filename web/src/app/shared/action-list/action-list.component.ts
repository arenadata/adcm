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
import { MatDialogRef } from '@angular/material/dialog';
import { openClose } from '@app/core/animations';
import { ApiService } from '@app/core/api';
import { Entities, IAction } from '@app/core/types';
import { Observable } from 'rxjs';

import { DialogComponent } from '../components/dialog.component';
import { DynamicComponent } from '../directives';

@Component({
  selector: 'app-action-list',
  styles: [
    'mat-card {margin:10px 10px 0;display: inline-block; min-width: 240px; min-height: 70px; max-width: 480px; vertical-align: top; overflow: hidden;}',
    'mat-card-header {justify-content: space-between;}',
    'mat-card-title {font-size: 18px;}',
    'button {margin-left: 8px;}',
  ],
  template: `
    <mat-card class="mat-expansion-panel">
      <mat-card-header>
        <mat-card-title color="primary">Fruit</mat-card-title>
        <mat-card-subtitle>some description about this group actions</mat-card-subtitle>
        <button mat-icon-button (click)="fruit.expand = !fruit.expand"><mat-icon>list</mat-icon></button>
      </mat-card-header>
      <div #fruit [@openClose]="!!fruit.expand">
        <mat-card>
          <mat-card-header>
            <mat-card-title>Apple</mat-card-title>
            <mat-card-subtitle>description or some description about this action description or some description about this action</mat-card-subtitle>
            <button mat-icon-button color="warn"><mat-icon>play_circle_outline</mat-icon></button>
          </mat-card-header>
        </mat-card>

        <mat-card>
          <mat-card-header>
            <mat-card-title>Banana</mat-card-title>
            <mat-card-subtitle>description or some description about this action</mat-card-subtitle>
            <button mat-icon-button color="warn"><mat-icon>play_circle_outline</mat-icon></button>
          </mat-card-header>
        </mat-card>

        <mat-card>
          <mat-card-header>
            <mat-card-title>Fruit loops</mat-card-title>
            <mat-card-subtitle>description</mat-card-subtitle>
            <button mat-icon-button color="warn"><mat-icon>play_circle_outline</mat-icon></button>
          </mat-card-header>
        </mat-card>
      </div>
    </mat-card>

    <mat-card class="mat-expansion-panel">
      <mat-card-header>
        <mat-card-title>Vegetables</mat-card-title>
        <mat-card-subtitle>description or some description about this action some description about this action</mat-card-subtitle>
        <button mat-icon-button (click)="veg.expand = !veg.expand"><mat-icon>list</mat-icon></button>
      </mat-card-header>
      <div #veg [@openClose]="!!veg.expand">
        <mat-card>
          <mat-card-header>
            <mat-card-title>Green</mat-card-title>
            <mat-card-subtitle></mat-card-subtitle>
            <button mat-icon-button (click)="green.expand = !green.expand"><mat-icon>list</mat-icon></button>
          </mat-card-header>
          <div #green [@openClose]="!!green.expand">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Broccoli</mat-card-title>
                <mat-card-subtitle>some description about this action</mat-card-subtitle>
                <button mat-icon-button color="warn"><mat-icon>play_circle_outline</mat-icon></button>
              </mat-card-header>
            </mat-card>

            <mat-card>
              <mat-card-header>
                <mat-card-title>Brussels sprouts</mat-card-title>
                <mat-card-subtitle>some description about this action</mat-card-subtitle>
                <button mat-icon-button color="warn"><mat-icon>play_circle_outline</mat-icon></button>
              </mat-card-header>
            </mat-card>
          </div>
        </mat-card>

        <mat-card>
          <mat-card-header>
            <mat-card-title>Orange</mat-card-title>
            <mat-card-subtitle>some description</mat-card-subtitle>
            <button mat-icon-button (click)="orange.expand = !orange.expand"><mat-icon>list</mat-icon></button>
          </mat-card-header>
          <div #orange [@openClose]="!!orange.expand">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Pumpkins</mat-card-title>
                <mat-card-subtitle>some description about this action</mat-card-subtitle>
                <button mat-icon-button color="warn"><mat-icon>play_circle_outline</mat-icon></button>
              </mat-card-header>
            </mat-card>

            <mat-card>
              <mat-card-header>
                <mat-card-title>Carrots</mat-card-title>
                <mat-card-subtitle></mat-card-subtitle>
                <button mat-icon-button color="warn"><mat-icon>play_circle_outline</mat-icon></button>
              </mat-card-header>
            </mat-card>
          </div>
        </mat-card>
      </div>
    </mat-card>

    <mat-card *ngFor="let a of actions$ | async" class="mat-expansion-panel">
      <mat-card-header>
        <mat-card-title>{{ a.display_name }}</mat-card-title>
        <mat-card-subtitle>{{ a.description || 'some description about this action' }}</mat-card-subtitle>
        <button [appActions]="{ cluster: clusterData, actions: [a] }" mat-icon-button color="warn"><mat-icon>play_circle_outline</mat-icon></button>
      </mat-card-header>
    </mat-card>

    <!-- <button mat-stroked-button color="warn" [appForTest]="'action_btn'" *ngFor="let a of actions$ | async" [appActions]="{ cluster: clusterData, actions: [a] }">
      <span>{{ a.display_name }}</span>
    </button> -->

    <mat-dialog-actions class="controls">
      <button mat-raised-button color="primary" (click)="dialogRef.close()">Cancel</button>
    </mat-dialog-actions>
  `,
  animations: [openClose],
})
export class ActionListComponent implements OnInit, DynamicComponent {
  model: Entities;
  actions$: Observable<IAction[]>;

  constructor(private api: ApiService, public dialogRef: MatDialogRef<DialogComponent>) {}

  ngOnInit(): void {
    this.actions$ = this.api.get<IAction[]>(this.model.action);
  }

  get clusterData() {
    const { id, hostcomponent } = 'hostcomponent' in this.model && this.model.typeName === 'cluster' ? this.model : (this.model as any).cluster || {};
    return { id, hostcomponent };
  }
}
