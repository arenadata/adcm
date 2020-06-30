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
import { Router, NavigationStart } from '@angular/router';
import { getFirstAdminLogin, getRoot, isAuthenticated, loadRoot, State, getConnectStatus, socketInit, loadStack, loadProfile, getProfile, rootError } from '@app/core/store';
import { select, Store } from '@ngrx/store';
import { combineLatest } from 'rxjs';
import { filter, switchMap, tap } from 'rxjs/operators';

import { ConfigService, IVersionInfo } from '../config.service';
import { MatDialog } from '@angular/material/dialog';
import { ChannelService } from '../channel.service';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable()
export class AppService {
  constructor(
    private store: Store<State>,
    private config: ConfigService,
    private router: Router,
    private dialog: MatDialog,
    private channel: ChannelService,
    public snackBar: MatSnackBar
  ) {}

  getRootAndCheckAuth() {
    this.store.dispatch(loadRoot());
    const b$ = this.store.pipe(select(getRoot));
    const a$ = this.store.pipe(select(isAuthenticated));
    return combineLatest([a$, b$]).pipe(
      filter((a) => a[0] && !!a[1]),
      switchMap((_) => this.config.load()),
      tap((c) => {
        if (!c) {
          this.channel.next('errorMessage', { title: 'New version available. Page has been refreshed.' });
          setTimeout(() => location.reload(), 2000);
        } else {
          this.store.dispatch(socketInit());
          this.store.dispatch(loadStack());
          this.store.dispatch(loadProfile());
        }
      })
    );
  }

  checkWSconnectStatus() {
    return this.store.pipe(
      select(getConnectStatus),
      filter((a) => !!a),
      tap(status => {
        if (status === 'open') this.channel.next('errorMessage', { title: 'Connection established.' });
        if (status === 'close') {
          this.channel.next('errorMessage', { title: 'Connection lost. Recovery attempt.' });
          this.store.dispatch(rootError());
        }
      })
    );
  }

  checkUserProfile() {
    return this.store.pipe(
      select(getProfile),
      filter((u) => u.settingsSaved)
    );
  }

  getVersion(versionData: IVersionInfo): IVersionInfo {
    return this.config.version.split('-').reduce((p, c, i) => ({ ...p, [Object.keys(versionData)[i]]: c }), {} as IVersionInfo);
  }

  initListeners() {
    // check user profile settings - this is the first entry
    this.store
      .pipe(
        select(getFirstAdminLogin),
        filter((u) => u)
      )
      .subscribe(() => this.router.navigate(['admin']));

    // close dialog
    this.router.events.pipe(filter((e) => e instanceof NavigationStart)).subscribe(() => this.dialog.closeAll());

    // error notification
    this.channel.on('errorMessage').subscribe((e) =>
      this.snackBar.open(`${e.title} ${e.subtitle || ''}`, 'Hide', {
        duration: 5000,
        panelClass: 'snack-bar-error',
      })
    );

    // test only
    // this.store
    //   .select(getMessage)
    //   .pipe(filter((e) => !!e))
    //   .subscribe((e) => console.log('EVENT:', e.event, { ...e.object, details: JSON.stringify(e.object.details) }));
  }
}
