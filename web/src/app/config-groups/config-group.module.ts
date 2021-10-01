import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConfigGroupListComponent } from './pages';
import { AdwpListModule } from '@adwp-ui/widgets';
import { AddConfigGroupComponent } from './components';
import { ReactiveFormsModule } from '@angular/forms';
import { MatListModule } from '@angular/material/list';
import { AddingModule } from '@app/shared/add-component/adding.module';
import { FormElementsModule } from '@app/shared/form-elements/form-elements.module';
import { ListService } from '../shared/components/list/list.service';
import { LIST_SERVICE_PROVIDER } from '../shared/components/list/list-service-token';
import { ConfigGroupHostListComponent } from './pages';
import { AddHostToConfigGroupComponent } from './components';
import { MatPaginatorModule } from '@angular/material/paginator';
import { ConfigGroupCheckboxComponent } from './components/config-group-checkbox/config-group-checkbox.component';
import { MatCheckboxModule } from '@angular/material/checkbox';


@NgModule({
  declarations: [
    ConfigGroupListComponent,
    AddConfigGroupComponent,
    ConfigGroupHostListComponent,
    AddHostToConfigGroupComponent,
    ConfigGroupCheckboxComponent
  ],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    AdwpListModule,
    MatListModule,
    AddingModule,
    FormElementsModule,
    MatPaginatorModule,
    MatCheckboxModule
  ],
  exports: [
    AddConfigGroupComponent,
    ConfigGroupCheckboxComponent,
  ],
  providers: [
    {
      provide: LIST_SERVICE_PROVIDER,
      useClass: ListService
    }
  ]
})
export class ConfigGroupModule {
}
