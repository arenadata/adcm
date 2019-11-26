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

import { environment } from '@env/environment';
import { Observable } from 'rxjs';

export interface User {
  username: string;
  password: string;
  confirm: string;
  change_password: string;
}

const USER_LINK = `${environment.apiRoot}user/`;

@Injectable()
export class UsersService {
  constructor(private http: HttpClient) {}

  public getUsers(): Observable<User[]> {
    return this.http.get<User[]>(USER_LINK);
  }

  public addUser(username: string, password: string): Observable<User> {
    return this.http.post<User>(USER_LINK, { username, password });
  }

  public clearUser(user: User): Observable<User> {
    return this.http.delete<User>(`${USER_LINK}${user.username}/`);
  }

  public changePassword(value: string, link: string): Observable<User> {
    return this.http.patch<User>(link, { 'password': value });
  }
}
