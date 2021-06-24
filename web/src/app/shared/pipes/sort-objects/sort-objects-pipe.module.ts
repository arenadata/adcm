import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SortObjectsPipe } from './sort-objects.pipe';


@NgModule({
  declarations: [SortObjectsPipe],
  imports: [
    CommonModule
  ],
  exports: [SortObjectsPipe]
})
export class SortObjectsPipeModule {
}
