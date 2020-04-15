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
import { Component, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ClusterService } from '@app/core';
import { Job } from '@app/core/types';
import { BaseDirective, ListComponent } from '@app/shared';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-job',
  template: `
    <mat-toolbar class="toolbar"><app-crumbs [navigation]="[{ path: '/task', name: 'jobs' }]"></app-crumbs></mat-toolbar>
    <div class="container-entry">
      <app-list #list class="main" [appBaseList]="'job'"></app-list>
    </div>
  `
})
export class JobComponent extends BaseDirective implements OnInit, OnDestroy {
  @ViewChild('list', { static: true }) list: ListComponent;
  ngOnInit(): void {
    this.list.listItemEvt
      .pipe(
        this.takeUntil(),
        filter(data => data.cmd === 'onLoad' && data.row)
      )
      .subscribe(data => localStorage.setItem('lastJob', data.row.id));
  }
}

@Component({
  selector: 'app-main',
  template: '<app-job-info></app-job-info>'
})
export class MainComponent implements OnInit {
  constructor(private details: ClusterService, private router: Router, private route: ActivatedRoute) {}

  ngOnInit() {
    const log = (<Job>this.details.Current).log_files[0];
    if (log) this.router.navigate([`../${log.id}`], { relativeTo: this.route });
  }
}
