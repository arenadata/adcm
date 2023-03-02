import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';

import { LoginCredentials } from '../models/login-credentials';

@Component({
  selector: 'adwp-login-form',
  templateUrl: './login-form.component.html',
  styleUrls: ['./login-form.component.scss']
})
export class LoginFormComponent {

  isNeedValidation = false;

  authForm = new FormGroup({
    username: new FormControl('', Validators.required),
    password: new FormControl('', Validators.required),
  });

  @Input() loginOverGoogle: boolean;
  @Input() message = '';

  @Output() auth = new EventEmitter<LoginCredentials>();

  login(): void {
    this.isNeedValidation = true;
    if (this.authForm.valid) {
      const credentials = this.authForm.value;
      this.auth.emit(credentials);
    }
  }

  google(): void {
    window.location.href = '/social/login/google-oauth2/';
  }

}
