
import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { MatListModule } from '@angular/material/list';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterModule } from '@angular/router';

import { TopMenuComponent } from './top-menu/top-menu.component';

@NgModule({
  declarations: [
    TopMenuComponent,
  ],
  imports: [
    CommonModule,
    RouterModule,
    MatToolbarModule,
    MatListModule,
  ],
  exports: [
    TopMenuComponent,
  ]
})
export class AdwpHeaderModule { }
