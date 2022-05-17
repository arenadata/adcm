import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacRolesAsOptionsDirective } from './rbac-roles-as-options.directive';


@NgModule({
  declarations: [RbacRolesAsOptionsDirective],
  imports: [
    CommonModule
  ],
  exports: [RbacRolesAsOptionsDirective]
})
export class RbacRolesAsOptionsModule {
}
