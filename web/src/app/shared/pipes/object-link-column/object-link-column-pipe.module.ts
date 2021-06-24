import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ObjectLinkColumnPipe } from './object-link-column.pipe';


@NgModule({
  declarations: [ObjectLinkColumnPipe],
  imports: [
    CommonModule
  ],
  exports: [ObjectLinkColumnPipe]
})
export class ObjectLinkColumnPipeModule {
}
