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
import { map } from 'rxjs/operators';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';

import { AuthService } from '../../core/auth/auth.service';
import { DialogComponent } from '@app/shared/components';
import { User, UsersService } from './users.service';

@Component({
  selector: 'app-users',
  templateUrl: './users.component.html',
  styles: ['.add-button {position: absolute; right: 40px;top: 10px;}', ':host {flex:1}'],
  providers: [UsersService],
})
export class UsersComponent implements OnInit {
  users: User[];
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

  constructor(private us: UsersService, private auth: AuthService, private router: Router, private dialog: MatDialog) {}

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
    this.currentUserName = this.auth.auth.login;
    this.us
      .getUsers()
      .pipe(map((u) => u.filter((a) => a.username !== 'status')))
      .subscribe((users) => (this.users = users));
  }

  addUser() {
    if (this.addForm.valid)
      this.us.addUser(this.addForm.get('username').value, this.addForm.get('xxx').get('password').value).subscribe((user) => {
        this.users = this.users.concat(user);
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
        this.us.clearUser(user).subscribe((_) => (this.users = this.users.filter((u) => u !== user)));
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
