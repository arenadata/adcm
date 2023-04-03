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
import {AbstractControl, FormControl, FormGroup, ValidationErrors, ValidatorFn, Validators} from '@angular/forms';
import { Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';

import { getProfileSelector, ProfileService, ProfileState } from '@app/core/store';
import { BaseDirective } from '@app/shared/directives';
import { IConfig } from "@app/shared/configuration/types";
import { ApiService } from "@app/core/api";
import {CustomValidators} from "@app/shared/validators/custom-validators";
import {passwordsConfirmValidator} from "@app/components/rbac/user-form/rbac-user-form.component";

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
          <adwp-input [form]="cpForm" label='Current password' controlName='current_password' type="password" ></adwp-input>
          <adwp-input [form]="cpForm" label='New password' controlName='password' type="password" ></adwp-input>
          <adwp-input [form]="cpForm" label='Confirm new password' controlName='confirm_password' type="password" ></adwp-input>
          <button mat-raised-button [disabled]="!cpForm.valid" (click)="changePassword()">Save</button>
        </div>
        <hr />
      </div>
    </div>
  `,
  styles: [
    ':host {flex: 1 }',
    '.container { padding-top: 40px; }',
    'hr { margin: 40px 0; border: 0; border-top: dashed 1px rgb(140, 140, 140); }',
    'h3, h4, h5 { font-weight: normal; }',
    'adwp-input { display: inline-flex; margin-right: 10px }'
  ],
})
export class ProfileComponent extends BaseDirective implements OnInit, OnDestroy {
  link: string;
  user$: Observable<ProfileState>;
  passMinLength = null;
  passMaxLength = null;

  passwordsConfirmValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
    const password = control.get('password');
    const confirm = control.get('confirm_password');

    return password && confirm && password.value !== confirm.value ? { passwordsNotMatch: true } : null;
  };

  cpForm = new FormGroup({
    current_password: new FormControl(null, [CustomValidators.required]),
    password: new FormControl(null, this.passwordValidators),
    confirm_password: new FormControl(null, this.passwordValidators),
  }, { validators: this.passwordsConfirmValidator });

  get passwordValidators() {
    return [
      CustomValidators.required,
      Validators.minLength(this.passMinLength || 3),
      Validators.maxLength(this.passMaxLength || 128),
      Validators.pattern(new RegExp(/^[\s\S]*$/u))
    ]
  }

  constructor(private router: Router, private store: Store<ProfileState>, private service: ProfileService, private api: ApiService) {
    super();
  }

  ngOnInit() {
    this.user$ = this.store.select(getProfileSelector).pipe(
      this.takeUntil()
    );

    this.getGlobalSettings().subscribe((resp) => {
      this.passMinLength = resp.config['auth_policy'].min_password_length;
      this.passMaxLength = resp.config['auth_policy'].max_password_length;

      this.cpForm.controls['password'].setValidators(this.passwordValidators);
      this.cpForm.controls['confirm_password'].setValidators(this.passwordValidators);
      this.cpForm.updateValueAndValidity();
    })
  }

  changePassword() {
    const password = this.cpForm.get('password').value;
    const currentPassword = this.cpForm.get('current_password').value;
    this.service.setPassword(password, currentPassword).subscribe(() => this.router.navigate(['/login']));
  }

  getGlobalSettings() {
    return this.api.get<IConfig>('/api/v1/adcm/1/config/current/?noview');
  }

}
