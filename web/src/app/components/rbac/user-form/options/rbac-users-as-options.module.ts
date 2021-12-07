import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UsersToOptionsPipe } from './users-to-options.pipe';
import { RbacUsersAsOptionsDirective } from './rbac-users-as-options.directive';



@NgModule({
  declarations: [UsersToOptionsPipe, RbacUsersAsOptionsDirective],
  exports: [
    UsersToOptionsPipe,
    RbacUsersAsOptionsDirective
  ],
  imports: [
    CommonModule
  ]
})
export class RbacUsersAsOptionsModule { }
