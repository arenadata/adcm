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

import { DynamicComponent } from '../directives';
import { Entities, IAction } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { Observable } from 'rxjs';
import { FlatTreeControl } from '@angular/cdk/tree';
import { MatTreeFlattener, MatTreeFlatDataSource } from '@angular/material/tree';
import { MatDialogRef } from '@angular/material/dialog';
import { DialogComponent } from '../components/dialog.component';

interface FoodNode {
  name: string;
  children?: FoodNode[];
}

const TREE_DATA: FoodNode[] = [
  {
    name: 'Fruit',
    children: [{ name: 'Apple' }, { name: 'Banana' }, { name: 'Fruit loops' }],
  },
  {
    name: 'Vegetables',
    children: [
      {
        name: 'Green',
        children: [{ name: 'Broccoli' }, { name: 'Brussels sprouts' }],
      },
      {
        name: 'Orange',
        children: [{ name: 'Pumpkins' }, { name: 'Carrots' }],
      },
    ],
  },
];

interface ExampleFlatNode {
  expandable: boolean;
  name: string;
  level: number;
}

@Component({
  selector: 'app-action-list',
  styles: ['button {margin: 10px;}', '.arrow {margin: 0}'],
  template: `
    <button mat-stroked-button color="warn" [appForTest]="'action_btn'" *ngFor="let a of actions$ | async" [appActions]="{ cluster: clusterData, actions: [a] }">
      <span>{{ a.display_name }}</span>
    </button>

    <mat-tree [dataSource]="dataSource" [treeControl]="treeControl">
      <mat-tree-node *matTreeNodeDef="let node" matTreeNodePadding>
        <button mat-stroked-button color="warn" onclick="alert('run action!')">
          <span>{{ node.name }}</span>
        </button>
      </mat-tree-node>
      <mat-tree-node *matTreeNodeDef="let node; when: hasChild" matTreeNodePadding>
        <button mat-stroked-button color="warn" onclick="alert('run action!')">
          <span>{{ node.name }}</span>
        </button>
        <button class="arrow" mat-icon-button matTreeNodeToggle [attr.aria-label]="'toggle ' + node.name">
          <mat-icon>
            {{ treeControl.isExpanded(node) ? 'expand_more' : 'chevron_right' }}
          </mat-icon>
        </button>
      </mat-tree-node>
    </mat-tree>

    <mat-dialog-actions class="controls">
      <button mat-raised-button color="primary" (click)="dialogRef.close()">Cancel</button>
    </mat-dialog-actions>
  `,
})
export class ActionListComponent implements OnInit, DynamicComponent {
  model: Entities;
  actions$: Observable<IAction[]>;

  isShow = false;

  treeControl = new FlatTreeControl<ExampleFlatNode>(
    (node) => node.level,
    (node) => node.expandable
  );

  treeFlattener = new MatTreeFlattener(
    (node: FoodNode, level: number) => ({
      expandable: !!node.children && node.children.length > 0,
      name: node.name,
      level: level,
    }),
    (node) => node.level,
    (node) => node.expandable,
    (node) => node.children
  );

  dataSource = new MatTreeFlatDataSource(this.treeControl, this.treeFlattener);

  hasChild = (_: number, node: ExampleFlatNode) => node.expandable;

  constructor(private api: ApiService, public dialogRef: MatDialogRef<DialogComponent>) {
    this.dataSource.data = TREE_DATA;
  }

  ngOnInit(): void {
    this.actions$ = this.api.get<IAction[]>(this.model.action);
  }

  get clusterData() {
    const { id, hostcomponent } = 'hostcomponent' in this.model && this.model.typeName === 'cluster' ? this.model : (this.model as any).cluster || {};
    return { id, hostcomponent };
  }
}
