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
import { Observable, Subject } from 'rxjs';
import { filter, map } from 'rxjs/operators';
import { HttpErrorResponse } from '@angular/common/http';

export enum keyChannelStrim {
  'scroll',
  'notifying',
  'load_complete',
  'error',
}

export interface IBroadcast<TKey = keyChannelStrim> {
  key: TKey;
  value: any;
}

export enum ResponseErrorLevel {
  Error = 'error',
}

export enum ResponseErrorCode {
  InvalidObjectDefinition = 'INVALID_OBJECT_DEFINITION',
  UserNotFound = 'USER_NOT_FOUND',
  AuthError = 'AUTH_ERROR',
  ConfigNotFound = 'CONFIG_NOT_FOUND',
}

export interface ResponseError extends HttpErrorResponse {
  error: {
    args?: string;
    desc?: string;
    detail?: string;
    code?: ResponseErrorCode;
    level?: ResponseErrorLevel;
  };
}

@Injectable({
  providedIn: 'root',
})
export class ChannelService<TKey = keyChannelStrim> {
  private event = new Subject<IBroadcast<TKey>>();

  next<T>(key: TKey, value: T) {
    this.event.next({ key, value });
  }

  on<T = any>(key: TKey): Observable<T> {
    return this.event.asObservable().pipe(
      filter((e) => e.key === key),
      map<IBroadcast<TKey>, T>((a) => a.value)
    );
  }
}
