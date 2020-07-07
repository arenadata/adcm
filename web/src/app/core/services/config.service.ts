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
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

const CONFIG_URL = '/assets/config.json';
export interface IVersionInfo {
  version: string;
  commit_id: string;
}

@Injectable({
  providedIn: 'root',
})
export class ConfigService {
  appConfig$: Observable<IVersionInfo>;

  constructor(private http: HttpClient) {}

  get version() {
    return localStorage.getItem('adcm:version') || '';
  }

  set version(version: string) {
    localStorage.setItem('adcm:version', version);
  }

  checkVersion(c: IVersionInfo): IVersionInfo {
    const version = `${c.version}-${c.commit_id}`;
    if (!this.version) this.version = version;
    else if (this.version !== version) {
      this.version = version;
      return null;
    }
    return c;
  }

  load() {
    return this.http.get<IVersionInfo>(`${CONFIG_URL}?nocache=${Date.now()}`).pipe(map((c) => this.checkVersion(c)));
  }
}
