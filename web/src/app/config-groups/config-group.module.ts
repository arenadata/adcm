import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConfigGroupHostListComponent, ConfigGroupListComponent } from './pages';
import { AdwpListModule } from '@app/adwp';
import { AddConfigGroupComponent, AddHostToConfigGroupComponent } from './components';
import { ReactiveFormsModule } from '@angular/forms';
import { MatListModule } from '@angular/material/list';
import { AddingModule } from '@app/shared/add-component/adding.module';
import { FormElementsModule } from '@app/shared/form-elements/form-elements.module';
import { ListService } from '../shared/components/list/list.service';
import { LIST_SERVICE_PROVIDER } from '../shared/components/list/list-service-token';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatCheckboxModule } from '@angular/material/checkbox';


@NgModule({
  declarations: [
    ConfigGroupListComponent,
    AddConfigGroupComponent,
    ConfigGroupHostListComponent,
    AddHostToConfigGroupComponent,
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
