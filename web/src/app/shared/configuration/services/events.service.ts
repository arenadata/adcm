import { Injectable } from '@angular/core';
import { ChannelService } from '@app/core/services';
import { Observable } from 'rxjs';
import { IFieldOptions, IPanelOptions } from '@app/shared/configuration/types';

export enum ConfigComponentChannelMessage {
  'LOAD_COMPLETE',
  'TOGGLE_ITEM'
}

@Injectable()
export class ConfigComponentChannelService extends ChannelService<ConfigComponentChannelMessage> {
}

@Injectable()
export class ConfigComponentEvents {
  isReady$: Observable<void> = this.channel.on(ConfigComponentChannelMessage.LOAD_COMPLETE);
  toggleItem$: Observable<(IPanelOptions & IFieldOptions) | IPanelOptions>
    = this.channel.on(ConfigComponentChannelMessage.TOGGLE_ITEM);

  constructor(protected channel: ConfigComponentChannelService) {}

  isLoaded(): void {
    this.channel.next(ConfigComponentChannelMessage.LOAD_COMPLETE, null);
  }

  toggleInGroup(data: (IPanelOptions & IFieldOptions) | IPanelOptions): void {
    this.channel.next(ConfigComponentChannelMessage.TOGGLE_ITEM, data);
  }
}
