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
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-entry-llist',
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="navigation()"></app-crumbs>
      <span class="example-spacer"></span>
      <app-add-button [name]="typeName" (added)="list.current = $event">{{ typeName === 'host' ? 'Add' : 'Create' }} {{ typeName }}</app-add-button>
    </mat-toolbar>
    <div class="container-entry">
      <app-list #list class="main" appActionHandler [appBaseList]="typeName"></app-list>
    </div>
  `,
  styles: [],
})
export class ListEntryComponent implements OnInit {
  typeName: string;

  constructor(private route: ActivatedRoute) {}

  ngOnInit() {
    const segments = this.route.snapshot.url.map(s => s.path);
    this.typeName = segments[0];
  }

  navigation() {
    return [{ url: `/${this.typeName}`, title: `${this.typeName}s` }];
  }
}
