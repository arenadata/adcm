import { Component, OnInit } from '@angular/core';
import { ApiService } from '@app/core/api';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';
import { RbacUserService } from '@app/services/rbac-user.service';
import { IConfig } from '../configuration/types';

const NO_FAILED_ATTEMPTS = 'There are no failed login attempts';
const ATTEMPTS_EXCEEDED = 'Failed login attempts are exceeded. Reset to 0';

@Component({
  selector: 'app-reset-login-attempts-button',
  templateUrl: './reset-login-attempts-button.component.html',
  styleUrls: ['./reset-login-attempts-button.component.scss']
})
export class ResetLoginAttemptsButtonComponent implements OnInit {
  loginAttemptsLimit: number;
  tooltip: string = NO_FAILED_ATTEMPTS;
  row: RbacUserModel;

  constructor(
    protected rbacUserService: RbacUserService,
    protected api: ApiService
  ) { }

  get failedLoginAttempts() {
    return this?.row?.failed_login_attempts;
  }

  get limitClass(): string {
    if (this.failedLoginAttempts === 0) {
      this.tooltip = NO_FAILED_ATTEMPTS;
    } else if (this.failedLoginAttempts >= this.loginAttemptsLimit) {
      this.tooltip = ATTEMPTS_EXCEEDED;
      return 'limit-exceed';
    } else if (this.failedLoginAttempts > 0 && this.failedLoginAttempts <= this.loginAttemptsLimit) {
      this.tooltip = `Failed login attempts are ${this.failedLoginAttempts}. Reset to 0`;
      return 'limit-acceptable';
    }
  }

  get isDisabled() {
    return !this.failedLoginAttempts || this.failedLoginAttempts === 0;
  }

  ngOnInit() {
    this.getGlobalSettings().subscribe((resp: IConfig) => {
      this.loginAttemptsLimit = resp.config['auth_policy'].login_attempt_limit
    })
  }

  resetFailureLoginAttempts(event) {
    event.stopPropagation();
    event.preventDefault();
    this.rbacUserService.resetLoginAttemps(this.row.id).subscribe(() => {
      this.tooltip = NO_FAILED_ATTEMPTS;
    });
  }

  getGlobalSettings() {
    return this.api.get<IConfig>('/api/v1/adcm/1/config/current/?noview');
  }
}
