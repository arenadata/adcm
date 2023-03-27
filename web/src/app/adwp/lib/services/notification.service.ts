import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable()
export class NotificationService {

  readonly SEPARATOR = '::';
  readonly INIT_STORAGE = 'init:notification';

  protected notification = new Subject<string>();

  constructor(
    public snackBar: MatSnackBar,
  ) { }

  setInitNotification(notification: string): void {
    localStorage.setItem(this.INIT_STORAGE, notification);
  }

  notify(notification: string): void {
    this.notification.next(notification);
  }

  error(notification: string): void {
    this.notify(`${notification}${this.SEPARATOR}error`);
  }

  on(): Observable<string> {
    return this.notification.asObservable();
  }

  private showInitialNotification(): void {
    if (localStorage.getItem(this.INIT_STORAGE)) {
      this.notify(localStorage.getItem(this.INIT_STORAGE));
      localStorage.removeItem(this.INIT_STORAGE);
    }
  }

  init(): void {
    this.notification.subscribe((m) => {
      const astr = m.split(this.SEPARATOR);
      const data = astr[1]
        ? { panelClass: 'snack-bar-error' }
        : {
          duration: 5000,
          panelClass: 'snack-bar-notify',
        };
      this.snackBar.open(astr[0], 'Hide', data);
    });
    this.showInitialNotification();
  }

}
