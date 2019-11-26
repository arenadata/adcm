import { TestBed } from '@angular/core/testing';

import { ChannelService } from './channel.service';

describe('ChannelService', () => {
  beforeEach(() => TestBed.configureTestingModule({}));

  it('should be created', () => {
    const service: ChannelService = TestBed.get(ChannelService);
    expect(service).toBeTruthy();
  });
});
