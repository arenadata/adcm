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
import { Injectable } from '@angular/core';
import { ApiService } from '@app/core/api';
import { IAction } from '@app/core/types';
import { FieldService } from '@app/shared/configuration/field.service';
import { ConfigFieldsComponent } from '@app/shared/configuration/fields/fields.component';
import { ServiceHostComponent } from '@app/shared/host-components-map/services2hosts/service-host.component';
import { Post } from '@app/shared/host-components-map/types';
import { IConfigAttr } from '@app/shared/configuration/types';

export interface IValue {
  config?: ConfigFieldsComponent;
  hostmap?: ServiceHostComponent;
}

export enum whatShow {
  none = 'none',
  config = 'config',
  hostMap = 'hostmap',
  stepper = 'stepper',
}

@Injectable()
export class MasterService {
  constructor(private api: ApiService, private configService: FieldService) {}

  spotShow(action: IAction): whatShow {
    const config = action.config?.config?.length;
    const hm = action.hostcomponentmap?.length;
    return config ? (hm ? whatShow.stepper : whatShow.config) : hm ? whatShow.hostMap : whatShow.none;
  }

  parseData(v: IValue) {
    const getData = (attr: IConfigAttr, c: ConfigFieldsComponent, h: ServiceHostComponent) => {
      const config = c ? this.configService.parseValue(c.form.value, c.rawConfig.config) : undefined;
      const hc = h?.statePost.data;
      return { attr, config, hc };
    };
    return v ? getData(v.config?.attr, v.config, v.hostmap) : undefined;
  }

  send(url: string, value: { config: any; hc: Post[] }) {
    return this.api.post(url, value);
  }
}
