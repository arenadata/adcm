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
import { ClusterService, StackService } from '@app/core';

@Component({
  selector: 'app-stack',
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="[{ url: '/bundle', title: 'bundles' }]"></app-crumbs>
      <app-button-uploader #uploadBtn [color]="'accent'" [label]="'Upload bundles'" (output)="upload($event)"></app-button-uploader>
    </mat-toolbar>
    <app-list #list [appBaseList]="typeName"></app-list>
  `,
  styles: [':host { flex: 1; }'],
})
export class StackComponent {
  typeName = 'bundle';
  @ViewChild('uploadBtn', { static: true }) uploadBtn: any;
  constructor(private stack: StackService) {}
  upload(data: FormData[]) {
    this.stack.upload(data).subscribe();
  }
}

@Component({
  selector: 'app-main',
  template: `
    <table>
      <tr *ngFor="let prop of keys(model)">
        <td style="padding: 6px 20px;">{{ prop }}</td>
        <td>{{ model[prop] }}</td>
      </tr>
    </table>
  `,
})
export class MainComponent implements OnInit {
  model: any;
  constructor(private service: ClusterService) {}

  ngOnInit() {
    this.model = this.service.Current;
  }

  keys(model: {}) {
    return Object.keys(model);
  }
}
