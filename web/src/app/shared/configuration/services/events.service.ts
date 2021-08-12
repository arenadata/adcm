import { Injectable } from '@angular/core';
import { ChannelService } from '@app/core/services';
import { Observable } from 'rxjs';

export enum ConfigComponentChannelMessage {
  'LOAD_COMPLETE',
  'ADD_TO_GROUP'
}

@Injectable()
export class ConfigComponentChannelService extends ChannelService<ConfigComponentChannelMessage> {
}

@Injectable()
export class ConfigComponentEvents {
  isReady$: Observable<void> = this.channel.on(ConfigComponentChannelMessage.LOAD_COMPLETE);

  constructor(protected channel: ConfigComponentChannelService) {}

  isLoaded(): void {
    this.channel.next(ConfigComponentChannelMessage.LOAD_COMPLETE, null);
  }
}
