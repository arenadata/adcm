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
import { IAction } from '@app/core/types';
import { Observable } from 'rxjs';

import { ActionsService } from '../actions.service';

@Component({
  selector: 'app-action-list',
  templateUrl: './action-list.component.html',
  styleUrls: ['./action-list.component.scss']
})
export class ActionListComponent {
  @Input() cluster: { id: number; hostcomponent: string };
  @Input() disabled: boolean;
  @Input() asButton = false;
  @Input() actionLink: string;
  @Input() state: string;

  /**
   * @deprecated in the fight against caching
   */
  @Input() actions = [];

  actions$: Observable<IAction[]>;

  constructor(private service: ActionsService) {}

  getData(): void {
    // if (!this.actions.length) ADCM-1505 it's possible cache after finished job
    this.actions$ = this.service.getActions(this.actionLink); //.subscribe((a) => (this.actions = a));
  }
}
