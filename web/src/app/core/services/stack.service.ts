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
import { ApiService } from '@app/core/api';
import { ApiState, getStack } from '@app/core/store';
import { Bundle } from '@app/core/types';
import { environment } from '@env/environment';
import { select, Store } from '@ngrx/store';
import { combineLatest, Observable } from 'rxjs';
import { filter, map, mergeMap, switchMap } from 'rxjs/operators';
import { ListResult } from '@app/models/list-result';

export type StackInfo = 'cluster' | 'host' | 'provider' | 'service' | 'bundle' | 'prototype';

const UPLOAD_URL = `${environment.apiRoot}stack/upload/`,
  LOAD_URL = `${environment.apiRoot}stack/load/`;

@Injectable({ providedIn: 'root' })
export class StackService {
  constructor(private api: ApiService, private store: Store<ApiState>) {}

  fromStack<T>(name: StackInfo, param?: { [key: string]: string | number }): Observable<T[]> {
    const params = Object.keys(param).reduce<any>((p, c) => ({ ...p, [c]: param[c] }), {});
    return this.store.pipe(
      select(getStack),
      filter((a) => a && !!Object.keys(a).length),
      switchMap((s) => this.api.get<ListResult<T>>(s[name], params).pipe(
        map((a) => a.results)))
    );
  }

  upload(output: FormData[]) {
    const item = (form: FormData) => {
      return this.api.post(UPLOAD_URL, form).pipe(
        mergeMap(() => this.api.post<Bundle>(LOAD_URL, { bundle_file: (form.get('file') as File).name }))
      );
    };
    return combineLatest(output.map((o) => item(o)));
  }
}
