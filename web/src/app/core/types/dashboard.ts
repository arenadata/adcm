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
import { IButton } from './button';

class Dashboard {
  id: number;
  userId: number;
  widgets: Widget[];
}

export interface Widget {
  id: number | undefined;
  type: string;
  title: string;
  height?: number;
  actions?: IButton[];
}

export const PROFILE_DASHBOARD_DEFAULT = [
  [
    [
      // {
      //   type: 'stack',
      //   title: 'BUNDLES',
      // },
    ],
    [
      // {
      //   type: 'cluster',
      //   title: 'CLUSTERS',
      //   actions: [
      //     { name: 'cluster', title: 'To view list clusters', type: 'link', icon: 'view_list' },
      //     { name: 'addCluster', title: 'Add cluster', color: 'accent', icon: 'library_add' },
      //   ],
      // },
    ],
    [
      // {
      //   type: 'host',
      //   title: 'HOSTS',
      //   actions: [
      //     { name: 'host', title: 'To view list hosts', type: 'link', icon: 'view_list' },
      //     { name: 'addHost', title: 'Add host', color: 'accent', icon: 'library_add' },
      //   ],
      // },
    ],
  ],

  [[], []],
  [[]],
  [{ type: 'intro', title: 'Hi there!' }],
];
