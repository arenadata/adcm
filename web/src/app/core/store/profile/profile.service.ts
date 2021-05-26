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
import { environment } from '@env/environment';
import { Observable, throwError } from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { AuthService } from '../../auth/auth.service';
import { PROFILE_DASHBOARD_DEFAULT } from '../../types/dashboard';

const PROFILE_LINK = `${environment.apiRoot}profile/`;

export interface IProfile {
  dashboard: any[];
  textarea: { [key: string]: number };
  settingsSaved: boolean;
}

export interface IUser {
  username: string;
  change_password: string;
  profile: IProfile;
}

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private user: IUser;

  constructor(private http: HttpClient, private auth: AuthService) {}

  public getProfile(): Observable<IUser> {
    const source$ = this.http.get<IUser>(`${PROFILE_LINK}${this.auth.auth.login}/`).pipe(
      map(user => (!user.profile ? { ...user, profile: this.emptyProfile() } : user)),
      tap(user => (this.user = user))
    );
    return this.auth.auth.login ? source$ : throwError('Not authorized!');
  }

  emptyProfile() {
    return { dashboard: PROFILE_DASHBOARD_DEFAULT, textarea: {}, settingsSaved: false };
  }

  setUser(key: string, value: string | boolean | { [key: string]: number }) {
    const profile = { ...this.user.profile };
    profile[key] = value;
    this.user = { ...this.user, profile };
  }

  public setProfile(): Observable<IUser> {
    const { username, profile } = { ...this.user };
    return this.http.patch<IUser>(`${PROFILE_LINK}${this.user.username}/`, { username, profile });
  }

  public setDashboardProfile(dashboard: any[]) {
    this.user.profile.dashboard = dashboard;
    return this.setProfile();
  }

  public setTextareaProfile(data: { key: string; value: number }) {
    const textarea = { ...this.user.profile.textarea };
    textarea[data.key] = data.value;
    this.setUser('textarea', textarea);
    return this.setProfile();
  }

  public addUser(user: { username: string; profile: string }): Observable<IUser> {
    return this.http.post<IUser>(`${PROFILE_LINK}`, user);
  }

  public defaultProfile() {
    this.user.profile.dashboard = PROFILE_DASHBOARD_DEFAULT;
    return this.setProfile();
  }

  public setPassword(password: string) {
    return this.http.patch(this.user.change_password, { password });
  }
}
