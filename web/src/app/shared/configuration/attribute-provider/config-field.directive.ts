import { Directive, TemplateRef } from '@angular/core';

@Directive({
  selector: '[appConfigField]'
})
export class ConfigFieldMarker {

  constructor(public template: TemplateRef<any>) {}

}
