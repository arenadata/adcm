import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GroupsToOptionsPipe } from './groups-to-options.pipe';
import { RbacGroupsAsOptionsDirective } from './rbac-groups-as-options.directive';


@NgModule({
  declarations: [GroupsToOptionsPipe, RbacGroupsAsOptionsDirective],
  exports: [
    GroupsToOptionsPipe,
    RbacGroupsAsOptionsDirective
  ],
  imports: [
    CommonModule
  ]
})
export class RbacGroupsAsOptionsModule {
}
