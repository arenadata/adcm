import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { filter, map, startWith } from 'rxjs/operators';
import { ConfigComponentEvents } from '@app/shared/configuration/services/events.service';
import { IFieldOptions, IPanelOptions } from '@app/shared/configuration/types';


@Injectable()
export class ConfigGroupsService {
  private _currentGroupKeys: { [key: string]: boolean } = {};

  groupKeys$: Observable<{ [key: string]: boolean }> = this.events.toggleItem$.pipe(
    startWith(),
    filter(v => !!v),
    map((item) => this._toggleItemInGroup(item))
  );

  constructor(private events: ConfigComponentEvents) {}

  next(groupKeys: { [key: string]: any }): void {
    this._currentGroupKeys = groupKeys;
  }

  private _toggleItemInGroup(item: IPanelOptions | (IPanelOptions & IFieldOptions)): { [key: string]: boolean } {
    const value = this._currentGroupKeys[item.key];

    this._currentGroupKeys = { ...this._currentGroupKeys, [item.key]: !value };

    return this._currentGroupKeys;
  };
}
