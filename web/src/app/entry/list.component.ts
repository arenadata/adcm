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
  selector: 'app-entry-list',
  template: `
    <mat-toolbar class="toolbar">
      <app-crumbs [navigation]="navigation()"></app-crumbs>
      <app-add-button [name]="typeName" (added)="list.current = $event">Create {{ typeName }}</app-add-button>
    </mat-toolbar>
    <app-list #list appActionHandler [appBaseList]="typeName"></app-list>
  `,
  styles: [':host { flex: 1; }'],
})
export class ListEntryComponent implements OnInit {
  typeName: string;

  constructor(private route: ActivatedRoute) {}

  ngOnInit() {
    const segments = this.route.snapshot.url.map((s) => s.path);
    this.typeName = segments[0];
  }

  navigation() {
    return [{ url: `/${this.typeName}`, title: `${this.typeName}s` }];
  }
}
