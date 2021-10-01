import { ChangeDetectionStrategy, Component, Input, TemplateRef } from '@angular/core';

@Component({
  selector: 'app-group-keys-wrapper',
  template: `
    <div class="group-keys-wrapper">
      <div class="group-checkbox">
        group-checkbox
        <app-config-group-checkbox></app-config-group-checkbox>
      </div>
      <div class="group-field">
        group-field
        <ng-container *ngTemplateOutlet="field"></ng-container>
      </div>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class GroupKeysWrapperComponent {

  @Input() public field: TemplateRef<any>;

}
