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
import { FormControl, FormGroup, NgModel, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { IColumns } from '@adwp-ui/widgets';
import { Store } from '@ngrx/store';

import { AuthService } from '@app/core/auth/auth.service';
import { DialogComponent } from '@app/shared/components';
import { User, UsersService } from './users.service';
import { AdwpListDirective } from '@app/abstract-directives/adwp-list.directive';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';
import { ListService } from '@app/shared/components/list/list.service';
import { SocketState } from '@app/core/store';
import { TypeName } from '@app/core/types';

@Component({
  selector: 'app-users',
  templateUrl: './users.component.html',
  styleUrls: ['users.component.scss'],
  providers: [UsersService],
})
export class UsersComponent extends AdwpListDirective<RbacUserModel> implements OnInit {

  listColumns = [
    {
      label: 'Username',
      sort: 'username',
      value: (row) => row.username,
    },
    {
      label: 'Email',
      sort: 'email',
      value: (row) => row.email,
    },
    {
      label: 'Groups',
      value: (row) => row.groups.join(', '),
    }
  ] as IColumns<RbacUserModel>;

  type: TypeName = 'rbac_user';

  // users: User[];
  hideLeft = true;
  showChangePassword = false;
  currentUserName: string;

  chPassword = new FormGroup({
    password: new FormControl('', [Validators.required]),
    cpassword: new FormControl('', [Validators.required]),
  });

  addForm = new FormGroup({
    username: new FormControl('', [Validators.required, Validators.pattern('[a-zA-Z0-9]*')]),
    xxx: this.chPassword,
  });

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,

    private us: UsersService,
    private auth: AuthService,
  ) {
    super(service, store, route, router, dialog);
  }

  get username() {
    return this.addForm.get('username');
  }

  get password() {
    return this.addForm.get('xxx').get('password');
  }

  get cpassword() {
    return this.addForm.get('xxx').get('cpassword');
  }

  ngOnInit() {
    super.ngOnInit();
    this.currentUserName = this.auth.auth.login;
    // this.us
    //   .getUsers()
    //   .pipe(map((u) => u.filter((a) => a.username !== 'status')))
    //   .subscribe((users) => (this.users = users));
  }

  addUser() {
    if (this.addForm.valid)
      this.us.addUser(this.addForm.get('username').value, this.addForm.get('xxx').get('password').value).subscribe((user) => {
        // this.users = this.users.concat(user);
        this.addForm.reset();
        this.hideLeft = true;
      });
  }

  clearUser(user: User) {
    const dialogRef = this.dialog.open(DialogComponent, {
      width: '250px',
      data: {
        text: `Delete [ ${user.username} ]? Are you sure?`,
        controls: ['Yes', 'No'],
      },
    });

    dialogRef.beforeClosed().subscribe((yes) => {
      if (yes) {
        // this.us.clearUser(user).subscribe((_) => (this.users = this.users.filter((u) => u !== user)));
      }
    });
  }

  validRow(pass: NgModel, cpass: NgModel): boolean {
    return pass.valid && cpass.valid && pass.value === cpass.value;
  }

  changePassword(user: User) {
    this.us.changePassword(user.password, user.change_password).subscribe((_) => {
      user.password = '';
      user.confirm = '';
      if (user.username === this.currentUserName) this.router.navigate(['/login']);
    });
  }
}
