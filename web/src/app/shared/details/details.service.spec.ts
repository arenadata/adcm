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
import { convertToParamMap, ParamMap, Params } from '@angular/router';
import { ClusterService } from '@app/core';
import { ApiService } from '@app/core/api';

type pages = 'cluster' | 'host' | 'provider' | 'service' | 'job' | 'bundle';

const mockParams = [{}, { cluser: 1 }, { service: 1 }, { cluser: 1, service: 1 }, null];

describe('DetailsService', () => {
  const service: ClusterService = new ClusterService({} as ApiService);
  const input = (params: Params): ParamMap => convertToParamMap(params);

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  /**
   * обработать входящие параметры,
   *  - проверить наличае кластера (cluster_id)
   *  - проверить текущий объект (current_id, typeName)
   *  - сравнить новые параметры с текущими _currentParamMap
   * обновить модель данных для компонента
   * сохранить их в свойство _currentParamMap
   *
   */

  /**
   * Модель данных для компонента
   *  toolbar: {
   *     crumbs: [],
   *     actions: [],
   *     upgradable: boolean,
   *     issues: boolean
   *  },
   *  left: {title: string, url: string, status: number, issue: boolean}[],
   *  title: (): string,
   *  subtitle: (): string
   */
});
