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
import { Component, OnDestroy, OnInit } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { ApiService } from '@app/core/api';
import { getProfileSelector, settingsSave, State } from '@app/core/store';
import { IConfig } from '@app/core/types';
import { BaseDirective } from '@app/shared';
import { select, Store } from '@ngrx/store';
import { exhaustMap, filter, map } from 'rxjs/operators';

@Component({
  selector: 'app-pattern',
  template: `
    <div>
      <mat-toolbar class="toolbar">
        <app-crumbs [navigation]="crumbs"></app-crumbs>
        <div class="example-spacer"></div>
      </mat-toolbar>
      <div class="row main">
        <mat-nav-list class="col-4">
          <a
            mat-list-item
            [appForTest]="'tab_' + item.url"
            *ngFor="let item of leftMenu"
            [routerLink]="[item.url]"
            routerLinkActive="active"
            >{{ item.title }}
          </a>
        </mat-nav-list>
        <mat-card class="col-8">
          <mat-card-header [style.minHeight.px]="40">
            <mat-card-title>{{ title }}</mat-card-title>
          </mat-card-header>
          <mat-card-content class="content">
            <router-outlet></router-outlet>
          </mat-card-content>
        </mat-card>
      </div>
    </div>
  `,
  styles: [
    '.main {position: absolute;top: 50px;bottom: 0;left: 5px;right: 5px;display: flex;margin-bottom: 5px;}',
    '.main mat-nav-list {padding-top: 20px;} ',
    '.main mat-card {display: flex;flex-direction: column;padding: 20px;}',
    '.content {flex-grow: 1;overflow: auto;padding-right:20px;}',
  ],
})
export class PatternComponent extends BaseDirective implements OnInit, OnDestroy {
  title = '';
  crumbs = [];
  leftMenu = [
    { url: 'intro', title: 'Intro' },
    { url: 'settings', title: 'Settings' },
    { url: 'users', title: 'Users' },
  ];
  data = {
    '/admin/intro': { title: 'Hi there!', crumbs: [{ path: '/admin/', name: 'intro' }] },
    '/admin/settings': { title: '', crumbs: [{ path: '/admin/settings', name: 'settings' }] },
    '/admin/users': { title: '', crumbs: [{ path: '/admin/users', name: 'users' }] },
  };

  constructor(private store: Store<State>, private api: ApiService, private router: Router) {
    super();
  }

  ngOnInit() {
    this.getContext(this.router.routerState.snapshot.url);

    this.router.events
      .pipe(
        filter(e => e instanceof NavigationEnd),
        this.takeUntil()
      )
      .subscribe((e: NavigationEnd) => this.getContext(e.url));

    // auto-save and flag in to profile
    this.store
      .pipe(
        select(getProfileSelector),
        filter(p => p.username === 'admin' && !p.profile.settingsSaved),
        exhaustMap(() =>
          this.api.get<IConfig>('/api/v1/adcm/1/config/current/').pipe(
            map(
              config =>
                config.config.find(f => f.name === 'global' && f.subname === 'adcm_url').value ||
                `${location.protocol}//${location.host}`
            ),
            exhaustMap(adcm_url =>
              this.api.post('/api/v1/adcm/1/config/history/', {
                config: { global: { send_stats: true, adcm_url } },
              })
            )
          )
        ),
        this.takeUntil()
      )
      .subscribe(() => this.store.dispatch(settingsSave({ isSet: true })));
  }

  getContext(url: string) {
    const a = this.data[url] || { title: '', crumbs: [] };
    this.title = a.title;
    this.crumbs = a.crumbs;
  }
}
