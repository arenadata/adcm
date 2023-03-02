import { Injectable } from '@angular/core';
import { Store } from '@ngrx/store';
import { select } from '@ngrx/store';
import { filter, take, takeUntil, tap } from 'rxjs/operators';

import { StatusType } from '../store/socket/socket.actions';
import { getConnectStatus } from '../store/socket/socket.selectors';
import { interval, merge, Observable } from 'rxjs';
import { NotificationService } from './notification.service';
import { isAuthenticated } from '../store/auth/auth.selectors';
import { SocketService } from './socket.service';
import { ConfigService } from './config.service';

@Injectable()
export class AppService {

  projectName: string;

  constructor(
    private store: Store,
    private notificationService: NotificationService,
    private socketService: SocketService,
    private configService: ConfigService,
  ) {}

  checkNewVersion(): Observable<string | null> {
    return this.configService.checkVersion().pipe(
      tap(newVersion => {
        if (newVersion) {
          this.notificationService.notify(`${this.projectName} will be upgraded in 2 seconds.`);
          this.notificationService.setInitNotification(`${this.projectName} has been upgraded`);
          setTimeout(() => location.reload(), 2000);
        }
        return newVersion;
      })
    );
  }

  checkWSConnectStatus(): Observable<StatusType> {
    return this.store.pipe(
      select(getConnectStatus),
      filter((a) => !!a),
      tap((status) => {
        if (status === StatusType.Open) {
          this.checkNewVersion().subscribe((newVersion) => {
            if (!newVersion) {
              this.notificationService.notify('Connection established.');
            }
          });
        }
        if (status === StatusType.Lost) {
          this.notificationService.error('Connection lost. Recovery attempt.');
          interval(4000)
            .pipe(takeUntil(merge(
              this.store.pipe(select(isAuthenticated), filter(state => !state), take(1)),
              this.store.pipe(select(getConnectStatus), filter(state => state === StatusType.Open), take(1)),
            )))
            .subscribe(() => {
              this.notificationService.error('No connection to back-end. Check your internet connection.');
              this.socketService.init();
            });
        }
      })
    );
  }

  checkAuthStatus(): Observable<boolean> {
    return this.store.pipe(
      select(isAuthenticated),
      tap(isAuth => {
        if (isAuth) {
          this.socketService.init();
        } else {
          this.socketService.close();
        }
      }),
    );
  }

  init(): void {
    this.checkWSConnectStatus().subscribe();
    this.checkAuthStatus().subscribe();
  }

}
