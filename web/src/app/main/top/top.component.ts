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
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { NavigationStart, Router } from '@angular/router';
import { PreloaderService } from '@app/core';
import { ApiService } from '@app/core/api';
import { authLogout, AuthState, EventMessage, getMessage, isAuthenticated, SocketState } from '@app/core/store';
import { select, Store } from '@ngrx/store';
import { Observable, of } from 'rxjs';
import { filter, switchMap, tap } from 'rxjs/operators';

interface JobStat {
  running: number;
  success: number;
  failed: number;
}

@Component({
  selector: 'app-top',
  templateUrl: './top.component.html',
  styleUrls: ['./top.component.scss'],
})
export class TopComponent implements OnInit {
  isAuth$: Observable<boolean> = of(false);
  jobStat$: Observable<JobStat>;
  jobStatus: JobStat = { running: 0, success: 0, failed: 0 };
  lastJob: string;

  @Output()
  onburger = new EventEmitter();

  constructor(
    private router: Router,
    private authStore: Store<AuthState>,
    private socketStore: Store<SocketState>,
    private api: ApiService,
    private preloader: PreloaderService
  ) {}

  ngOnInit() {
    this.isAuth$ = this.authStore.select(isAuthenticated);

    this.initStat();

    this.socketStore
      .pipe(
        select(getMessage),
        filter(
          (m: EventMessage) =>
            m &&
            m.event === 'change_job_status' &&
            m.object.type === 'task' &&
            ['running', 'success', 'failed'].includes(m.object.details.value)
        ),
        tap(() => (this.jobStat$ = this.getJobStat(localStorage.getItem('lastJob') || '0')))
      )
      .subscribe();

    this.router.events
      .pipe(filter(e => e instanceof NavigationStart && !e.url.includes('task')))
      .subscribe(() => this.initStat());
  }

  initStat() {
    const lastJob = localStorage.getItem('lastJob') || '0';
    if (lastJob !== this.lastJob) this.jobStat$ = this.getJobStat(lastJob);
  }

  getJobStat(lastJob: string) {
    this.preloader.freeze();
    return this.api.root.pipe(
      switchMap(root =>
        this.api.get<JobStat>(`${root.stats}task/${lastJob}/`).pipe(
          tap(job => {
            this.jobStatus = job;
            this.lastJob = lastJob;
          })
        )
      )
    );
  }

  profile() {
    this.router.navigate(['profile']);
  }

  logout() {
    this.authStore.dispatch(authLogout());
  }

  burger() {
    this.onburger.emit('sidenav.toggle');
  }
}
