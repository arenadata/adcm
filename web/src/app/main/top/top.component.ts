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
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable, of } from 'rxjs';

import { authLogout, AuthState, isAuthenticated } from '@app/core/store';

@Component({
  selector: 'app-top',
  templateUrl: './top.component.html',
  styleUrls: ['./top.component.scss'],
})
export class TopComponent implements OnInit {
  isAuth$: Observable<boolean> = of(false);

  constructor(
    private router: Router,
    private authStore: Store<AuthState>,
  ) {}

  ngOnInit() {
    this.isAuth$ = this.authStore.select(isAuthenticated);
  }

  profile() {
    this.router.navigate(['profile']);
  }

  logout() {
    this.authStore.dispatch(authLogout());
  }

}
