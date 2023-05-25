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
import { IRequires } from '@app/core/types';

@Component({
  selector: 'app-dependencies',
  template: `
    <ul>
      <li *ngFor="let item of items">
        {{ item?.display_name }}
        <app-dependencies [components]="item?.components"></app-dependencies>
      </li>
    </ul>
  `,
  styles: ['li {padding: 6px 0;}'],
})
export class DependenciesComponent implements OnInit {
  // by dialog window
  model: IRequires[];
  items: IRequires[];

  @Input() components: IRequires[];

  ngOnInit(): void {
    this.items = this.model || this.components;
  }
}
