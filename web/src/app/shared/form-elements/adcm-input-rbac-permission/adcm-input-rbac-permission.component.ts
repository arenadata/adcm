import { Component, Input } from '@angular/core';
import { FormGroup } from '@angular/forms';
import { AdwpStringHandler } from '@adwp-ui/widgets';

@Component({
  selector: 'adcm-input-rbac-permission',
  templateUrl: './adcm-input-rbac-permission.component.html',
  styleUrls: ['./adcm-input-rbac-permission.component.scss']
})
export class AdcmInputRbacPermissionComponent<T> {
  @Input() form: FormGroup;

  @Input() controlName: string;

  @Input() multiple: boolean;

  @Input() label: string;

  @Input() handler: AdwpStringHandler<T>;

  @Input() isRequired = false;

  open = false;

  isError(name: string): boolean {
    const f = this.form.get(name);
    return f.invalid && (f.dirty || f.touched);
  }

  hasError(name: string, error: string): boolean {
    return this.form.controls[name].hasError(error);
  }
}
