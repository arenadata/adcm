import { PolymorpheusContent } from '@tinkoff/ng-polymorpheus';
import { Observable } from 'rxjs';
import { AdwpDropdownWidthT } from '../types';
import { AdwpHorizontalDirection, AdwpVerticalDirection } from '../types';

export interface AdwpDropdown<C = object> {
  refresh$: Observable<any>;
  clientRect: ClientRect;
  content: PolymorpheusContent;
  host: HTMLElement;
  align: AdwpHorizontalDirection;
  minHeight: number;
  maxHeight: number;
  direction?: AdwpVerticalDirection | null;
  limitMinWidth?: AdwpDropdownWidthT;
  sided?: boolean;
  fixed?: boolean;
  context?: C;
}
