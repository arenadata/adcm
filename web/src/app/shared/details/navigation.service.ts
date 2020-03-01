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
import { ApiBase, Issue, Job } from '@app/core/types';

import { IDetails } from './details.service';
import { ThemePalette } from '@angular/material/core';


const ISSUE_MESSAGE = 'Something is wrong with your cluster configuration, please review it.';

const IssueSet: { [key: string]: string[] } = {
  service: ['required_service'],
  import: ['required_import']
};

type IconMenu = 'issue' | 'status';

interface Icon {
  id: IconMenu;
  isShow: boolean;
  color: ThemePalette;
  name: string;
}

export interface INavItem {
  id?: number;
  title: string;
  url: string;
  issue?: string;
  status?: number;
  statusMessage?: string;
}

export const Config = {
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
    bundle: [{ id: 0, title: 'Main', url: 'main' }],
    job: [{ id: 0, title: 'Main', url: 'main' }]
  }
};

@Injectable()
export class NavigationService {
  getLeft(current: Partial<ApiBase>): INavItem[] {
    const typeName = current.typeName;
    if (typeName === 'job') {
      const job = current as Job;
      return [{ id: 0, title: 'Main', url: 'main' }, ...job.log_files.map(a => ({ title: a.file, url: `${a.tag}_${a.level}` }))];
    }

    const issue = current.issue || {} as Issue;    
    return Config.menu[typeName].map((i: INavItem) => ({
      ...i,
      issue: this.findIssue(i.url, issue),
      status: +current.status
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
          id: cluster.id,
          url: pref,
          title: cluster.name,
          issue: this.getIssueMessage(cluster.issue && !!Object.keys(cluster.issue).length)
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

  getIssueMessage(flag: boolean) {
    return flag ? ISSUE_MESSAGE : '';
  }

  findIssue(url: string, issue: Issue) {
    return Object.keys(issue).some(p => p === url || (IssueSet[url] && IssueSet[url].some(a => a === p)));
  }
}
