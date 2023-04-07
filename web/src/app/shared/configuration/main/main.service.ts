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
import { Injectable, Injector } from '@angular/core';
import { isObject, TypeName } from '@app/core/types';
import { FieldService, IOutput, TFormOptions } from '../services/field.service';
import { CompareConfig, IFieldOptions, IFieldStack } from '../types';
import { ConfigService, IConfigService } from '@app/shared/configuration/services/config.service';
import { ClusterService } from '@app/core/services/cluster.service';
import { ConfigGroupService } from '@app/config-groups/service/config-group.service';

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

@Injectable({
  providedIn: 'root'
})
export class MainService {
  configService: IConfigService;

  constructor(private fields: FieldService,
              public cluster: ClusterService,
              private injector: Injector) {
    const current: TypeName | undefined = cluster.Current?.typeName;
    if (current === 'group_config') {
      this.configService = injector.get(ConfigGroupService);
    } else {
      this.configService = injector.get(ConfigService);
    }
  }

  get worker$() {
    return this.cluster.worker$;
  }

  get Current() {
    return this.cluster.Current;
  }

  getConfig(url: string) {
    return this.configService.getConfig(url);
  }

  changeVersion(url: string, id: number) {
    return this.configService.changeVersion(id, url);
  }

  changeService(type) {
    if (type === 'group_config') {
      this.configService = this.injector.get(ConfigGroupService);
    } else {
      this.configService = this.injector.get(ConfigService);
    }
  }

  filterApply(options: TFormOptions[], search: ISearchParam) {
    this.fields.filterApply(options, search);
  }

  parseValue(output: IOutput, source: IFieldStack[]) {
    return this.fields.parseValue(output, source);
  }

  send(url: string, data: any) {
    return this.configService.send(url, data);
  }

  getHistoryList(url: string) {
    return this.configService.getHistoryList(url);
  }

  compareConfig(ids: number[], dataOptions: TFormOptions[], compareConfig: CompareConfig[], configUrl: string) {
    dataOptions.map((a) => this.runClear(a, ids));
    const cc = ids.map((id) => compareConfig.find((a) => a.id === id));

    this.changeVersion(configUrl, ids[0]).subscribe((resp) => {
      const mockConfig = this.fields.toFormGroup(this.fields.getPanels(resp));
      dataOptions.map((a) => this.runCheck(a, cc, mockConfig.value));
    });
  }

  runClear(a: TFormOptions, ids: number[]) {
    if ('options' in a) a.options.map((b) => this.runClear(b, ids));
    else if (a.compare.length) a.compare = a.compare.filter((b) => ids.includes(b.id));
    return a;
  }

  runCheck(a: TFormOptions, configs: CompareConfig[], mockConfig: IFieldStack[]) {
    if ('options' in a) a.options.map((b) => this.runCheck(b, configs, mockConfig));
    else this.checkField(a, configs, mockConfig);
    return a;
  }

  checkField(a: IFieldOptions, configs: CompareConfig[], mockConfig: IFieldStack[]) {
    configs
      .filter((b) => a.compare.every((e) => e.id !== b.id))
      .map((c) => {
        const co = this.findFieldCompare(a.key, { ...c, config: mockConfig });
        console.log(co)
        if (!co) {
          if (String(a.value) && String(a.value) !== 'null') a.compare.push({
            id: c.id,
            date: c.date,
            color: c.color,
            value: 'null'
          });
        } else {
          if (isObject(co.value)) {
            if (isObject(a.value)) {
              if (JSON.stringify(a.value) !== JSON.stringify(co.value)) a.compare.push({
                ...co,
                value: JSON.stringify(co.value)
              });
            } else if (typeof a.value === 'string') {
              if (JSON.stringify(JSON.parse(a.value)) !== JSON.stringify(co.value)) a.compare.push({
                ...co,
                value: JSON.stringify(co.value)
              });
            }
          } else if (String(co.value) !== String(a.value)) a.compare.push(co);
        }
      });
    return a;
  }

  findFieldCompare(key: string, cc: CompareConfig) {
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
