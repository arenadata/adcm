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
import { animate, state, style, transition, trigger } from '@angular/animations';
import { Injectable } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { ApiService } from '@app/core/api';
import { ClusterService } from '@app/core/services';
import { Observable } from 'rxjs';

import { FieldService } from '../field.service';
import { FieldOptions, FieldStack, IConfig, PanelOptions } from '../types';

export interface ISearchParam {
  advanced: boolean;
  search: string;
}

export const historyAnime = [
  trigger('history', [
    state('hide', style({ top: '130px' })),
    state('show', style({ top: '200px' })),
    state('hideTools', style({ opacity: 0 })),
    state('showTools', style({ opacity: 0.8 })),
    transition('hideTools => showTools', animate('.5s .3s ease-in')),
    transition('showTools => hideTools', animate('.2s ease-out')),
    transition('hide <=> show', animate('.3s')),
  ]),
];

@Injectable()
export class MainService {
  constructor(private fields: FieldService, private api: ApiService, private current: ClusterService) {}

  get Current() {
    return this.current.Current;
  }

  getConfig(url: string): Observable<IConfig> {
    return this.api.get<IConfig>(url);
  }

  filterApply(options: (FieldOptions | PanelOptions)[], search: ISearchParam) {
    this.fields.filterApply(options, search);
  }

  parseValue(form: FormGroup, raw: FieldStack[]) {
    return this.fields.parseValue(form, raw);
  }

  send(url: string, data: any) {
    return this.api.post<IConfig>(url, data);
  }
}
