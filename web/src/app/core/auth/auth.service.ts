import { Observable } from 'rxjs';
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
import { environment } from '@env/environment';
import { throwError } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { ApiService } from '../api';

@Injectable()
export class AuthService {
  public get token(): string {
    return this.auth.token;
  }

  public get auth() {
    const auth = localStorage.getItem('auth') || '';
    return auth ? JSON.parse(auth) : { login: '', token: '' };
  }

  public set auth(value: { login: string; token: string }) {
    localStorage.setItem('auth', JSON.stringify(value));
  }

  public redirectUrl: string;

  constructor(private api: ApiService) {}

  checkGoogle() {
    return this.api.get<{google_oauth: boolean}>(`${environment.apiRoot}info/`).pipe(map(a => a.google_oauth));
  }

  login(login: string, password: string): Observable<{ token: string }> {
    return this.api.post(`${environment.apiRoot}token/`, { username: login, password }).pipe(
      tap((response: { token: string }) => {
        let token = response && response.token;
        if (token) {
          this.auth = { login, token };
        }
      }),
      catchError(err => {
        this.auth = { login: '', token: '' };
        return throwError(err);
      })
    );
  }

  logout() {
    this.auth = { login: '', token: '' };
  }
}
