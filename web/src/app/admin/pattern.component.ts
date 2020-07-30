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
import { BaseDirective } from '@app/shared';
import { IConfig } from '@app/shared/configuration/types';
import { select, Store } from '@ngrx/store';
import { exhaustMap, filter } from 'rxjs/operators';

@Component({
  selector: 'app-pattern',
  template: `
    <mat-toolbar>
      <app-crumbs [navigation]="crumbs"></app-crumbs>
      <div class="example-spacer"></div>
    </mat-toolbar>
    <mat-drawer-container [style.flex]="1" autosize>
      <mat-drawer disableClose="true" mode="side" opened [style.backgroundColor]="'transparent'" [style.minWidth.px]="200">
        <mat-nav-list [style.paddingTop.px]="20">
          <a mat-list-item [appForTest]="'tab_' + item.url" *ngFor="let item of leftMenu" [routerLink]="[item.url]" routerLinkActive="active">{{ item.title }} </a>
        </mat-nav-list>
      </mat-drawer>
      <mat-drawer-content [style.display]="'flex'">
        <mat-card>
          <mat-card-header>
            <mat-card-title>{{ title }}</mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <router-outlet></router-outlet>
          </mat-card-content>
        </mat-card>
      </mat-drawer-content>
    </mat-drawer-container>
  `,
  styleUrls: ['../shared/details/detail.component.scss'],
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
    '/admin': { title: 'Hi there!', crumbs: [{ path: '/admin/', name: 'intro' }] },
    '/admin/intro': { title: 'Hi there!', crumbs: [{ path: '/admin/', name: 'intro' }] },
    '/admin/settings': { title: 'Global configuration', crumbs: [{ path: '/admin/settings', name: 'settings' }] },
    '/admin/users': { title: 'User management', crumbs: [{ path: '/admin/users', name: 'users' }] },
  };

  constructor(private store: Store<State>, private api: ApiService, private router: Router) {
    super();
  }

  ngOnInit() {
    this.getContext(this.router.routerState.snapshot.url);

    this.router.events
      .pipe(
        filter((e) => e instanceof NavigationEnd),
        this.takeUntil()
      )
      .subscribe((e: NavigationEnd) => this.getContext(e.url));

    // auto-save and flag in to profile
    this.store
      .pipe(
        select(getProfileSelector),
        filter((p) => p.username === 'admin' && !p.profile.settingsSaved),
        exhaustMap(() =>
          this.api.get<IConfig>('/api/v1/adcm/1/config/current/?noview').pipe(
            exhaustMap((c) => {
              const config = c.config;
              const global = config['global'] || {};
              global.adcm_url = global.adcm_url || `${location.protocol}//${location.host}`;
              global.send_stats = true;
              return this.api.post('/api/v1/adcm/1/config/history/', c);
            })
          )
        ),
        this.takeUntil()
      )
      .subscribe(() => this.store.dispatch(settingsSave({ isSet: true })));
  }

  getContext(url: string) {
    const a = this.data[url];
    this.title = a.title;
    this.crumbs = a.crumbs;
  }
}
