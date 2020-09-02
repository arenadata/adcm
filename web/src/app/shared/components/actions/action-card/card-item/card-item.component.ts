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
import { openClose } from '@app/core/animations';

@Component({
  selector: 'app-card-item',
  template: `
    <ng-container *ngFor="let a of items">
      <mat-card *ngIf="a.children?.length; else branch" class="mat-expansion-panel">
        <mat-card-header>
          <mat-card-title>{{ a.display_name }}</mat-card-title>
          <mat-card-subtitle>{{ a.description }}</mat-card-subtitle>
          <button mat-icon-button (click)="a.expand = !a.expand"><mat-icon>list</mat-icon></button>
        </mat-card-header>
        <div [@openClose]="!!a.expand">
          <app-card-item [items]="a.children" [cluster]="cluster"></app-card-item>
        </div>
      </mat-card>
      <ng-template #branch>
        <mat-card>
          <mat-card-header>
            <mat-card-title>{{ a.display_name }}</mat-card-title>
            <mat-card-subtitle>{{ a.description }}</mat-card-subtitle>
            <button [appActions]="{ cluster: cluster, actions: [a] }" mat-icon-button color="accent"><mat-icon>play_circle_outline</mat-icon></button>
          </mat-card-header>
        </mat-card>
      </ng-template>
    </ng-container>
  `,
  styles: [
    'mat-card {margin:10px 10px 0;display: inline-block; min-width: 240px; min-height: 70px; max-width: 480px; vertical-align: top; overflow: hidden;}',
    'mat-card-header {justify-content: space-between;}',
    'mat-card-title {font-size: 18px;}',
    'button {margin-left: 8px;}',
  ],
  animations: [openClose],
})
export class CardItemComponent {
  @Input() items: any;
  @Input() cluster: { id: number; hostcomponent: string };
}
