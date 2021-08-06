import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConfigGroupRoutingModule } from './config-group-routing.module';
import { ConfigGroupListComponent } from './pages';
import { AdwpListModule } from '@adwp-ui/widgets';
import { AddConfigGroupComponent } from '@app/config-groups/components/config-group-add/config-group.component';
import { ReactiveFormsModule } from '@angular/forms';
import { Host2configgroupComponent } from '@app/config-groups/components/config-group-host-add/host2configgroup.component';
import { MatListModule } from '@angular/material/list';
import { AddingModule } from '@app/shared/add-component/adding.module';
import { FormElementsModule } from '@app/shared/form-elements/form-elements.module';


@NgModule({
  declarations: [ConfigGroupListComponent, AddConfigGroupComponent, Host2configgroupComponent],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    ConfigGroupRoutingModule,
    AdwpListModule,
    MatListModule,
    AddingModule,
    FormElementsModule
  ],
  exports: [
    AddConfigGroupComponent,
    Host2configgroupComponent
  ],
})
export class ConfigGroupModule {
}
