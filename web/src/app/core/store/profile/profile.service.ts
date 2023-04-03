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

import { AuthService } from '@app/core/auth/auth.service';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';

const PROFILE_LINK = `${environment.apiRoot}profile/`;

export interface LastViewedTask {
  id: number;
}

export interface IProfile {
  textarea: { [key: string]: number };
  settingsSaved: boolean;
  lastViewedTask?: LastViewedTask;
}

export interface IUser {
  username: string;
  change_password: string;
  profile: IProfile;
}

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private user: RbacUserModel;

  constructor(private http: HttpClient, private auth: AuthService) {}

  public getProfile(): Observable<IUser> {
    const source$ = this.me().pipe(
      map(user => (!user.profile ? { ...user, profile: this.emptyProfile() } : user)),
      tap(user => (this.user = user))
    );
    return this.auth.auth.login ? source$ : throwError('Not authorized!');
  }

  emptyProfile() {
    return { textarea: {}, settingsSaved: false };
  }

  setUser(key: string, value: string | boolean | { [key: string]: number }) {
    const profile = { ...this.user.profile };
    profile[key] = value;
    this.user = { ...this.user, profile };
  }

  me(): Observable<RbacUserModel> {
    return this.http.get<RbacUserModel>(`${environment.apiRoot}rbac/me/`);
  }

  setProfile(): Observable<RbacUserModel> {
    const { username, password, profile } = { ...this.user };
    return this.http.patch<RbacUserModel>(`${environment.apiRoot}rbac/me/`, { username, profile });
  }

  setTextareaProfile(data: { key: string; value: number }): Observable<IUser> {
    const textarea = { ...this.user.profile.textarea };
    textarea[data.key] = data.value;
    this.setUser('textarea', textarea);
    return this.setProfile();
  }

  setLastViewedTask(id: number): Observable<IUser> {
    this.setUser('lastViewedTask', { id });
    return this.setProfile();
  }

  addUser(user: { username: string; profile: string }): Observable<IUser> {
    return this.http.post<IUser>(`${PROFILE_LINK}`, user);
  }

  setPassword(password: string, currentPassword: string) {
    return this.http.patch(`${environment.apiRoot}rbac/me/`, { password, current_password: currentPassword });
  }
}
