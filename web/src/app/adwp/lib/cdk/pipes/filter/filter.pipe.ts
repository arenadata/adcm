import { Pipe, PipeTransform } from '@angular/core';
import { AdwpMatcher } from '../../types';

@Pipe({ name: 'adwpFilter' })
export class AdwpFilterPipe implements PipeTransform {
  /**
   * Filters an array through a matcher function using additional arguments
   *
   * @param items array
   * @param matcher method for filtering
   * @param args arbitrary number of additional arguments
   */
  transform<T>(items: readonly T[], matcher: AdwpMatcher<T>, ...args: any[]): T[] {
    return items.filter(item => matcher(item, ...args));
  }
}
