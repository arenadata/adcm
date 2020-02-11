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
import { WorkerInstance } from '@app/core';
import { ApiBase, Job } from '@app/core/types';

export interface CrumbsItem {
  path: string;
  name: string;
  issue?: string;
}

enum IssueProp {
  main,
  service,
  host,
  host_component,
  config,
}

const IssueSet: { [key: string]: string[] } = {
  service: ['required_service'],
  import: ['required_import'],
};

export interface ILeftMenuItem {
  id?: IssueProp;
  title: string;
  url: string;
  issue?: {
    message?: string;
    icon?: string;
  };
}

const Config = {
  menu: {
    cluster: [
      { id: 0, title: 'Main', url: 'main' },
      { id: 1, title: 'Services', url: 'service' },
      { id: 2, title: 'Hosts', url: 'host' },
      { id: 3, title: 'Hosts - Components', url: 'host_component' },
      { id: 4, title: 'Configuration', url: 'config' },
      { id: 5, title: 'Status', url: 'status' },
      { id: 6, title: 'Import', url: 'import' },
    ],
    service: [
      { id: 0, title: 'Main', url: 'main' },
      { id: 4, title: 'Configuration', url: 'config' },
      { id: 5, title: 'Status', url: 'status' },
      { id: 6, title: 'Import', url: 'import' },
    ],
    host: [{ id: 0, title: 'Main', url: 'main' }, { id: 4, title: 'Configuration', url: 'config' }, { id: 5, title: 'Status', url: 'status' }],
    provider: [{ id: 0, title: 'Main', url: 'main' }, { id: 4, title: 'Configuration', url: 'config' }],
    bundle: [{ id: 0, title: 'Main', url: 'main' }],
  },
};

export class NavigationService {

  getLeft(current: ApiBase): ILeftMenuItem[] {
    const typeName = current.typeName;
    if (typeName === 'job') {
      const job = current as Job;
      return [{ id: 0, title: 'Main', url: 'main' }, ...job.log_files.map(a => ({ title: a.file, url: `${a.tag}_${a.level}` }))];
    }

    const issue = current.issue || {};
    return Config.menu[typeName].map((i: ILeftMenuItem) => ({
      ...i,
      issue: Object.keys(issue).some(p => p === i.url || (IssueSet[i.url] && IssueSet[i.url].some(a => a === p))),
      status: current.status,
    }));
  }

  getCrumbs(model: WorkerInstance): CrumbsItem[] {
    let output: CrumbsItem[] = [],
      pref = '';

    if (model.cluster) {
      pref = `/cluster/${model.cluster.id}`;
      output = [
        { path: '/cluster', name: 'clusters' },
        {
          path: pref,
          name: model.cluster.name,
          issue:
            model.cluster.issue && !!Object.keys(model.cluster.issue).length ? `Something is wrong with your cluster configuration, please review it.` : '',
        },
      ];
    }

    const c = model.current as any;
    const typeName = c.typeName === 'job' ? 'task' : c.typeName;

    if (model.current.typeName !== 'cluster')
      output = [
        ...output,
        { path: `${pref}/${typeName}`, name: model.current.typeName + 's' },
        {
          path: `${pref}/${model.current.typeName}/${model.current.id}`,
          name: c.display_name || c.name || c.fqdn || c.action.name,
        },
      ];

    return output;
  }
}
