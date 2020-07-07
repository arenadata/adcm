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
import { ApiService } from '@app/core/api';
import { sendMetrics, State } from '@app/core/store';
import { ApiBase } from '@app/core/types/api';
import { DynamicEvent } from '@app/shared';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { map, switchMap } from 'rxjs/operators';

@Component({
  selector: 'app-settings',
  template: '<app-config-form *ngIf="set$ | async as set" [configUrl]="set.config" (event)="onEvent($event)"></app-config-form>',
  styles: [':host {flex:1; display: flex;}'],
})
export class SettingsComponent implements OnInit {
  set$: Observable<any>;

  constructor(private api: ApiService, private store: Store<State>) {}

  ngOnInit() {
    this.set$ = this.api.root.pipe(
      switchMap((root) => this.api.get<ApiBase>(root.adcm)),
      map((adcm) => adcm[0])
    );
  }

  onEvent(e: DynamicEvent) {
    if (e.name === 'send') this.store.dispatch(sendMetrics({ metrics: e.data.form.controls['send_stats/global'].value }));
  }
}
