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
import { ApiBase, Job } from '@app/core/types';

import { IDetails, INavItem } from './details.service';

const IssueSet: { [key: string]: string[] } = {
  service: ['required_service'],
  import: ['required_import']
};

const Config = {
  menu: {
    cluster: [
      { id: 0, title: 'Main', url: 'main' },
      { id: 1, title: 'Services', url: 'service' },
      { id: 2, title: 'Hosts', url: 'host' },
      { id: 3, title: 'Hosts - Components', url: 'host_component' },
      { id: 4, title: 'Configuration', url: 'config' },
      { id: 5, title: 'Status', url: 'status' },
      { id: 6, title: 'Import', url: 'import' }
    ],
    service: [
      { id: 0, title: 'Main', url: 'main' },
      { id: 4, title: 'Configuration', url: 'config' },
      { id: 5, title: 'Status', url: 'status' },
      { id: 6, title: 'Import', url: 'import' }
    ],
    host: [
      { id: 0, title: 'Main', url: 'main' },
      { id: 4, title: 'Configuration', url: 'config' },
      { id: 5, title: 'Status', url: 'status' }
    ],
    provider: [
      { id: 0, title: 'Main', url: 'main' },
      { id: 4, title: 'Configuration', url: 'config' }
    ],
    bundle: [{ id: 0, title: 'Main', url: 'main' }]
  }
};

export class NavigationService {
  getLeft(current: ApiBase): INavItem[] {
    const typeName = current.typeName;
    if (typeName === 'job') {
      const job = current as Job;
      return [{ id: 0, title: 'Main', url: 'main' }, ...job.log_files.map(a => ({ title: a.file, url: `${a.tag}_${a.level}` }))];
    }

    const issue = current.issue || {};
    return Config.menu[typeName].map((i: INavItem) => ({
      ...i,
      issue: Object.keys(issue).some(p => p === i.url || (IssueSet[i.url] && IssueSet[i.url].some(a => a === p))),
      status: current.status
    }));
  }

  getCrumbs(current: IDetails): INavItem[] {
    //model: { cluster: { id: number; name: string; issue: Issue }; current: { id: number; typeName: string; name: string } }

    let output: INavItem[] = [],
      pref = '';

    if (current.parent || current.typeName === 'cluster') {
      const cluster = current.parent || current;
      pref = `/cluster/${cluster.id}`;
      output = [
        { url: '/cluster', title: 'clusters' },
        {
          url: pref,
          title: cluster.name,
          issue: cluster.issue && !!Object.keys(cluster.issue).length ? `Something is wrong with your cluster configuration, please review it.` : ''
        }
      ];
    }

    const typeName = current.typeName === 'job' ? 'task' : current.typeName;

    if (current.typeName !== 'cluster')
      output = [
        ...output,
        { url: `${pref}/${typeName}`, title: `${current.typeName}s` },
        {
          url: `${pref}/${current.typeName}/${current.id}`,
          title: current.name
        }
      ];

    return output;
  }
}
