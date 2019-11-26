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
      <app-crumbs [navigation]="[{ path: '/bundle', name: 'bundles' }]"></app-crumbs>
      <span class="example-spacer"></span>
      <div style="margin-right: 6px;">
        <app-button-uploader #uploadBtn [color]="'accent'" [label]="'Upload bundles'" (output)="upload($event)"></app-button-uploader>
      </div>
    </mat-toolbar>
    <div class="container-entry">
      <app-list #list class="main" [appBaseList]="typeName"></app-list>
    </div>
  `,
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
  styles: [],
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
