import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacUsersAsOptionsDirective } from './rbac-users-as-options.directive';


@NgModule({
  declarations: [RbacUsersAsOptionsDirective],
  exports: [
    RbacUsersAsOptionsDirective
  ],
  imports: [
    CommonModule
  ]
})
export class RbacUsersAsOptionsModule {
}
