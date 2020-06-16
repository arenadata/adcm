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
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { getProfileSelector, ProfileService, ProfileState } from '@app/core/store';
import { BaseDirective } from '@app/shared';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-profile',
  template: `
    <div class="container">
      <div *ngIf="user$ | async as user">
        <p>
          You are authorized as [ <b>{{ user.username }}</b> ]
        </p>
        <hr />
        <div [formGroup]="cpForm">
          <h3>Change Password</h3>
          <mat-form-field>
            <input
              matInput
              placeholder="Password"
              formControlName="password"
              (input)="cpForm.get('cpassword').updateValueAndValidity()"
              type="password"
            />
          </mat-form-field>
          &nbsp;
          <mat-form-field>
            <input
              matInput
              placeholder="Confirm password"
              formControlName="cpassword"
              appConfirmEqualValidator="password"
              type="password"
            />
          </mat-form-field>
          &nbsp;
          <button mat-raised-button [disabled]="!cpForm.valid" (click)="changePassword()">Save</button>
        </div>
        <hr />
      </div>
    </div>
  `,
  styles: [
    '.container { padding-top: 40px; }',
    'hr { margin: 40px 0; border: 0; border-top: dashed 1px rgb(140, 140, 140); }',
    'h3, h4, h5 { font-weight: normal; }',
  ],
})
export class ProfileComponent extends BaseDirective implements OnInit, OnDestroy {
  link: string;
  user$: Observable<ProfileState>;

  cpForm = new FormGroup({
    password: new FormControl('', Validators.required),
    cpassword: new FormControl('', Validators.required),
  });

  constructor(private router: Router, private store: Store<ProfileState>, private service: ProfileService) {
    super();
  }

  ngOnInit() {
    this.user$ = this.store.select(getProfileSelector).pipe(
      this.takeUntil()
    );
  }

  changePassword() {
    const password = this.cpForm.get('password').value;
    this.service.setPassword(password).subscribe(() => this.router.navigate(['/login']));
  }

  // flatten(arr) {
  //   return flatten<Widget>(arr);
  // }
}
