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
import { Injectable, NgZone } from '@angular/core';
import { NavigationStart, Router } from '@angular/router';
import { interval } from 'rxjs';
import { distinctUntilChanged, filter, map, startWith, take, tap } from 'rxjs/operators';

@Injectable({
  providedIn: 'root',
})
export class FullyRenderedService {
  navStart$ = this.router.events
    .pipe(
      filter((event) => event instanceof NavigationStart),
      startWith(null as string), // Start with something, because the app doesn't fire this on appload, only on subsequent route changes
      tap((event) => {
        /* Place code to track NavigationStart here */
      })
    )
    .subscribe();

  constructor(private router: Router, private zone: NgZone) {}

  /**
   *
   *
   * @param {() => void} callback
   * @memberof FullyRenderedService
   */
  stableView(callback: () => void) {
    this.zone.runOutsideAngular(() => {
      interval(10)
        .pipe(
          startWith(0),
          // To prevent a memory leak on two closely times route changes, take until the next nav start
          //takeUntil(this.navigationStart$),
          // Turn the interval number into the current state of the zone
          map(() => !this.zone.hasPendingMacrotasks),
          // Don't emit until the zone state actually flips from `false` to `true`
          distinctUntilChanged(),
          // Filter out unstable event. Only emit once the state is stable again
          filter((stateStable) => stateStable === true),
          // Complete the observable after it emits the first result
          take(1),
          tap((stateStable) => {
            //console.log('FULLY RENDERED!!!!');
            callback();
          })
        )
        .subscribe();
    });
  }
}
