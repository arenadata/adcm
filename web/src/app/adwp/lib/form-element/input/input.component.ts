import { Component, Input } from '@angular/core';
import { FormGroup } from '@angular/forms';

@Component({
  selector: 'adwp-input',
  templateUrl: './input.component.html',
  styleUrls: ['./input.component.scss'],
})
export class AdwpInputComponent {
  @Input() form: FormGroup;
  @Input() controlName: string;
  @Input() label: string;
  @Input() isRequired = false;
  @Input() type: 'button' | 'checkbox' | 'file' | 'hidden' | 'image' | 'password' | 'radio' | 'reset' | 'submit' | 'text' = 'text';

  isError(name: string): boolean {
    const f = this.form.get(name);
    return f.invalid && (f.dirty || f.touched);
  }

  hasError(name: string, error: string): boolean {
    return this.form.controls[name].hasError(error);
  }
}
