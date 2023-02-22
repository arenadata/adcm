import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable} from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { IVersionInfo } from '../models/version-info';

const CONFIG_URL = '/assets/config.json';

@Injectable()
export class ConfigService {

  readonly VERSION_STORAGE = 'version';

  constructor(private http: HttpClient) {}

  get version(): string {
    return localStorage.getItem(this.VERSION_STORAGE) || '';
  }

  set version(version: string) {
    localStorage.setItem(this.VERSION_STORAGE, version);
  }

  getVersion(versionData: IVersionInfo): IVersionInfo {
    const arrVersion = this.version.split('-');
    return arrVersion.length > 1 ? {
      version: arrVersion[0],
      commit_id: arrVersion[1],
    } : null;
  }

  hasNewVersion(): Observable<string | null> {
    return this.http.get<IVersionInfo>(`${CONFIG_URL}?nocache=${Date.now()}`).pipe(
      map((configVersion: IVersionInfo) => {
        const newVersion = `${configVersion.version}-${configVersion.commit_id}`;
        return !this.version || this.version !== newVersion ? newVersion : null;
      }),
    );
  }

  checkVersion(): Observable<string | null> {
    return this.hasNewVersion().pipe(tap(version => {
      if (version) {
        this.version = version;
      }
    }));
  }

}
