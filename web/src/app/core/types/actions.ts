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
import { IConfig } from '@app/shared/configuration/types';

/**
 *
 *```
{
    action: 'add' | 'remove';
    component: string;    // name of servise to work with
    service: string;      // name of component to work with
}
```
 *
 */
export interface IActionParameter {
  action: 'add' | 'remove';
  component: string;
  service: string;
}

export interface IUIOptions {
  disclaimer?: string;
}

export interface IAction {
  name: string;
  description: string;
  display_name: string;
  start_impossible_reason: string;
  run: string;
  config: IConfig;
  hostcomponentmap: IActionParameter[];
  button: 'create_host' | null;
  ui_options: IUIOptions;
  children?: IAction[];
}
