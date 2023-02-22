import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { LoadingComponent } from './loading.component';

@NgModule({
  declarations: [
    LoadingComponent,
  ],
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
  ],
  exports: [
    LoadingComponent,
  ]
})
export class AdwpLoadingModule { }
