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
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NavigationStart, Router } from '@angular/router';
import { ConfigService, IConfig, Message, MessageService } from '@app/core';
import {
  getConnectStatus,
  getFirstAdminLogin,
  getMessage,
  getRoot,
  isAuthenticated,
  loadProfile,
  loadRoot,
  loadStack,
  rootError,
  socketInit,
  State,
} from '@app/core/store';
import { select, Store } from '@ngrx/store';
import { combineLatest, Observable } from 'rxjs';
import { filter, tap } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  template: `
    <app-top></app-top>
    <app-tooltip></app-tooltip>
    <main>
      <app-progress></app-progress>
      <mat-sidenav-container class="drawer">
        <router-outlet></router-outlet>
      </mat-sidenav-container>
    </main>
    <footer>
      <div>
        <span class="left" *ngIf="config$ | async as conf">
          VERSION:
          <a target="_blank" href="https://docs.arenadata.io/adcm/notes.html#{{ conf.version }}">{{ conf.version }}-{{ conf.commit_id }}</a></span
        >
        <span>ARENADATA &copy; {{ currentYear }}</span>
      </div>
    </footer>
  `,
})
export class AppComponent implements OnInit {
  currentYear = new Date().getFullYear();
  version: string;
  config$: Observable<IConfig>;

  constructor(
    public snackBar: MatSnackBar,
    private store: Store<State>,
    private message: MessageService,
    private config: ConfigService,
    private router: Router,
    private dialog: MatDialog
  ) {}

  ngOnInit() {
    this.store.dispatch(loadRoot());
    const b$ = this.store.pipe(select(getRoot));
    const a$ = this.store.pipe(select(isAuthenticated));
    combineLatest([a$, b$])
      .pipe(filter(a => a[0] && !!a[1]))
      .subscribe(() => {
        this.message.ignoreMessage = false;
        this.message.errorMessage({ title: 'Connection established.' });
        this.store.dispatch(socketInit());
        this.store.dispatch(loadStack());
        this.store.dispatch(loadProfile());
        this.config$ = this.config.config.pipe(tap(c => this.checkVersion(c.version)));
      });

    // check ws connect status
    this.store.pipe(select(getConnectStatus)).subscribe(status => {
      console.log('Socket status :: ', status);
      if (status === 'close') {
        this.message.errorMessage({ title: 'Connection lost. Recovery attempt.' });
        this.message.ignoreMessage = true;
        this.store.dispatch(rootError());
      }
    });

    // check user profile settings - this is the first entry
    this.store
      .pipe(
        select(getFirstAdminLogin),
        filter(u => u)
      )
      .subscribe(() => this.router.navigate(['admin']));

    // close dialog
    this.router.events.pipe(filter(e => e instanceof NavigationStart)).subscribe(() => this.dialog.closeAll());

    // error notification
    this.message.message$.subscribe((error: Message) =>
      this.snackBar.open(`${error.title} ${error.subtitle || ''}`, 'Hide', {
        duration: 5000,
        panelClass: 'snack-bar-error',
      })
    );

    // test only
    this.store
      .select(getMessage)
      .pipe(filter(e => !!e))
      .subscribe(e => console.log('EVENT:', e.event, { ...e.object, details: JSON.stringify(e.object.details) }));
  }

  checkVersion(version: string) {
    if (this.version && this.version !== version) {
      this.message.errorMessage({ title: 'New version available. Page has been refreshed.' });
      setInterval(() => location.reload(), 3000);
    } else this.version = version;
  }
}
