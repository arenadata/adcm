import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { FormControl } from '@angular/forms';

@Component({
  selector: 'app-config-group-checkbox',
  templateUrl: './config-group-checkbox.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConfigGroupCheckboxComponent {

  @Input() control: FormControl;

  @Input() disabled: boolean;

}
