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
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap, map, switchMap } from 'rxjs/operators';

const CONFIG_URL = '/assets/config.json';
export interface IConfig {
  version: string;
  commit_id: string;
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  appConfig$: Observable<IConfig>;

  constructor(private http: HttpClient) {}

  get version() {
    return localStorage.getItem('adcm:version');
  }

  set version(version: string) {
    localStorage.setItem('adcm:version', version);
  }

  get config() {
    return this.appConfig$.pipe(map(c => this.checkVersion(c)));
  }

  checkVersion(c: IConfig): IConfig | null {
    if (this.version !== c.version) {
      this.version = c.version;
      return null;
    } else return c;
  }

  load() {
    const ts = Date.now();
    this.appConfig$ = this.http.get<IConfig>(`${CONFIG_URL}?p=${ts}`);
  }
}
