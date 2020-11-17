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
import { ApiService } from '@app/core/api';
import { ClusterService } from '@app/core/services';
import { getRandomColor, isObject } from '@app/core/types';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

import { FieldService, IOutput, TFormOptions } from '../field.service';
import { CompareConfig, IConfig, IFieldOptions, IFieldStack } from '../types';

/**
 *```
  advanced: boolean;
  search: string;
  ```
 */
export interface ISearchParam {
  advanced: boolean;
  search: string;
}

export const historyAnime = [
  trigger('history', [
    state('hide', style({ top: '70px' })),
    state('show', style({ top: '134px' })),
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

  filterApply(options: TFormOptions[], search: ISearchParam) {
    this.fields.filterApply(options, search);
  }

  parseValue(output: IOutput, source: IFieldStack[]) {
    return this.fields.parseValue(output, source);
  }

  send(url: string, data: any) {
    return this.api.post<IConfig>(url, data);
  }

  getHistoryList(url: string, currentVersionId: number) {
    return this.api.get<IConfig[]>(url).pipe(map((h) => h.filter((a) => a.id !== currentVersionId).map((b) => ({ ...b, color: getRandomColor() }))));
  }

  compareConfig(ids: number[], dataOptions: TFormOptions[], compareConfig: CompareConfig[]) {
    dataOptions.map((a) => this.runClear(a, ids));
    const cc = ids.map((id) => compareConfig.find((a) => a.id === id));
    dataOptions.map((a) => this.runCheck(a, cc));
  }

  runClear(a: TFormOptions, ids: number[]) {
    if ('options' in a) a.options.map((b) => this.runClear(b, ids));
    else if (a.compare.length) a.compare = a.compare.filter((b) => ids.includes(b.id));
    return a;
  }

  runCheck(a: TFormOptions, configs: CompareConfig[]) {
    if ('options' in a) a.options.map((b) => this.runCheck(b, configs));
    else this.checkField(a, configs);
    return a;
  }

  checkField(a: IFieldOptions, configs: CompareConfig[]) {
    configs
      .filter((b) => a.compare.every((e) => e.id !== b.id))
      .map((c) => {
        const co = this.findFieldiCompare(a.key, c);
        if (!co) {
          if (String(a.value) && String(a.value) !== 'null') a.compare.push({ id: c.id, date: c.date, color: c.color, value: 'null' });
        } else {
          if (isObject(co.value)) {
            if (isObject(a.value)) {
              if (JSON.stringify(a.value) !== JSON.stringify(co.value)) a.compare.push({ ...co, value: JSON.stringify(co.value) });
            } else if (typeof a.value === 'string') {
              if (JSON.stringify(JSON.parse(a.value)) !== JSON.stringify(co.value)) a.compare.push({ ...co, value: JSON.stringify(co.value) });
            }
          } else if (String(co.value) !== String(a.value)) a.compare.push(co);
        }
      });
    return a;
  }

  findFieldiCompare(key: string, cc: CompareConfig) {
    const value = key
      .split('/')
      .reverse()
      .reduce((p, c) => p[c], cc.config);
    if (value !== null && value !== undefined && String(value)) {
      const { id, date, color } = { ...cc };
      return { id, date, color, value };
    }
  }
}
