import { InjectionToken } from '@angular/core';
import { AdwpDropdown } from '../interfaces/dropdown-directive';

export const ADWP_DROPDOWN_DIRECTIVE = new InjectionToken<AdwpDropdown>(
  'Directive controlling AdwpDropdownBoxComponent',
);
