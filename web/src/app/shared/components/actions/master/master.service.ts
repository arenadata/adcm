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
import { FieldStack } from '@app/shared/configuration/types';
import { ServiceHostComponent } from '@app/shared/host-components-map/services2hosts/service-host.component';

export interface IValue {
  config: ConfigFieldsComponent;
  hostmap: ServiceHostComponent;
}

export enum whatShow {
  none = 'none',
  config = 'config',
  hostMap = 'hostmap',
  stepper = 'stepper'
}

@Injectable()
export class MasterService {
  constructor(private api: ApiService, private configService: FieldService) {}

  spotShow(action: IAction): whatShow {
    const config = !!(action.config && action.config.config.length);
    const hm = !!action.hostcomponentmap;
    return config ? (!hm ? whatShow.config : whatShow.stepper) : hm ? (!config ? whatShow.hostMap : whatShow.stepper) : whatShow.none;
  }

  send(value: IValue, url: string, flag: boolean, rawConfig: FieldStack[]) {
    const data: any = {};
    if (value.config) data.value = value.config.form;
    if (value.hostmap) data.hostmap = value.hostmap.service.statePost.data;

    return flag
      ? this.api.post(url, {})
      : this.api.post(url, {
          // TODO: remove configService
          config: data.value ? this.configService.parseValue(data.value, rawConfig) : {},
          hc: data.hostmap
        });
  }
}
