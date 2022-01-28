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
import { BehaviorSubject, Observable } from 'rxjs';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';

export type IRouteHistory = string[];

@Injectable({
  providedIn: 'root'
})
export class RouterHistoryService {

  static HISTORY_DEPTH = 10;

  private readonly _history: BehaviorSubject<IRouteHistory>;

  readonly history: Observable<IRouteHistory>;

  constructor(private readonly _router: Router) {
    this._history = new BehaviorSubject<IRouteHistory>([]);
    this.history = this._history.asObservable();

    this._router.events.pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: NavigationEnd) => this._push(event));
  }

  reset(): void {
    this._history.next([]);
  }

  current(): string | null {
    const value = this._history.getValue();

    return (Array.isArray(value) && value[0]) ?? null;
  }

  previous(): string | null {
    const value = this._history.getValue();

    return (Array.isArray(value) && value[1]) ?? null;
  }

  private _push(event: NavigationEnd): void {
    const history = this._history.getValue();
    const url = event.urlAfterRedirects.split(';')[0];
    let value = history;

    if (!history[0] || history[0] !== url) {
      value = [url, ...history];

      if (value.length > RouterHistoryService.HISTORY_DEPTH) {
        value.pop();
      }
    }

    this._history.next(value);
  }
}
