import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RbacGroupsAsOptionsDirective } from './rbac-groups-as-options.directive';


@NgModule({
  declarations: [RbacGroupsAsOptionsDirective],
  exports: [
    RbacGroupsAsOptionsDirective
  ],
  imports: [
    CommonModule
  ]
})
export class RbacGroupsAsOptionsModule {
}
