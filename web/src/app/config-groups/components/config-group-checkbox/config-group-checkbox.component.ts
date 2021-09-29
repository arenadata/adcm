import { ChangeDetectionStrategy, Component, Input, OnInit } from '@angular/core';
import { FormControl } from '@angular/forms';

@Component({
  selector: 'app-config-group-checkbox',
  templateUrl: './config-group-checkbox.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConfigGroupCheckboxComponent implements OnInit {

  @Input() control: FormControl;

  @Input() disabled: boolean;

  ngOnInit(): void {
    console.log('sss', this.control);
  }

}
