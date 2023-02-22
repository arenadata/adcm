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
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { BaseDirective } from '@app/adwp';

import { ClusterService } from '@app/core/services/cluster.service';

@Component({
  selector: 'app-main',
  template: '<app-job-info></app-job-info>',
})
export class MainComponent extends BaseDirective implements OnInit {

  constructor(
    private clusterService: ClusterService,
    private router: Router,
    private route: ActivatedRoute,
  ) {
    super();
  }

  ngOnInit() {
    this.route.parent.params.pipe(this.takeUntil()).subscribe(params => {
      this.clusterService.one_job(params?.job).subscribe(job => {
        const logs = job.log_files;
        const log = logs.find((a) => a.type === 'check') || logs[0];
        if (log) this.router.navigate([`../${log.id}`], { relativeTo: this.route, replaceUrl: true });
      });
    });
  }

}
