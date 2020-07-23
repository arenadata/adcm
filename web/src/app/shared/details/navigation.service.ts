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
import { ApiBase, Issue, Job, TypeName } from '@app/core/types';

import { IDetails } from './details.service';
import { ThemePalette } from '@angular/material/core';

const ISSUE_MESSAGE = 'Something is wrong with your cluster configuration, please review it.';

const IssueSet: { [key: string]: string[] } = {
  service: ['required_service'],
  import: ['required_import'],
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
  action?: () => void;
}

const all = [
  { id: 0, title: 'Main', url: 'main' },
  { id: 4, title: 'Configuration', url: 'config' },
  { id: 5, title: 'Status', url: 'status' },
  { id: 6, title: 'Import', url: 'import' },
  { id: 1, title: 'Services', url: 'service' },
  { id: 2, title: 'Hosts', url: 'host' },
  { id: 3, title: 'Hosts - Components', url: 'host_component' },
];

const [main, config, m_status, m_import] = all;

export const Config = {
  menu: {
    cluster: all.sort((a, b) => a.id - b.id),
    service: [main, config, m_status, m_import],
    host: [main, config, m_status],
    provider: [main, config],
    bundle: [main],
  },
};

@Injectable()
export class NavigationService {
  findIssue = (url: string, issue: Issue) => Object.keys(issue).some((p) => p === url || (IssueSet[url] && IssueSet[url].some((a) => a === p)));
  getIssueMessage = (flag: boolean) => (flag ? ISSUE_MESSAGE : '');

  getLeft(current: Partial<ApiBase>): INavItem[] {
    const getMenu = (c: Partial<ApiBase>) => {
      const forJob = (job: Job) => [main, ...job.log_files.map((a) => ({ title: `${a.name} [ ${a.type} ]`, url: `${a.id}`, action: () => (location.href = a.download_url) }))];
      const def = (typeName: TypeName, issue: Issue, status: number) =>
        Config.menu[typeName].map((i: INavItem) => ({
          ...i,
          issue: this.findIssue(i.url, issue),
          status,
        }));

      return c.typeName === 'job' ? forJob(c as Job) : def(c.typeName, c.issue || ({} as Issue), +c.status);
    };

    return getMenu(current);
  }

  getCrumbs(current: IDetails): INavItem[] {
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
          issue: this.getIssueMessage(cluster.issue && !!Object.keys(cluster.issue).length),
        },
      ];
    }

    const typeName = current.typeName === 'job' ? 'task' : current.typeName;

    if (current.typeName !== 'cluster')
      output = [
        ...output,
        { url: `${pref}/${typeName}`, title: `${current.typeName}s` },
        {
          url: `${pref}/${current.typeName}/${current.id}`,
          title: current.name,
        },
      ];

    return output;
  }
}
