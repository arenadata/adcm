import { TestBed } from '@angular/core/testing';

import { IssueMessageService } from './issue-message.service';

describe('IssueMessageService', () => {
  let service: IssueMessageService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        IssueMessageService,
      ],
    });
    service = TestBed.inject(IssueMessageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('#parser should match', (done: DoneFn) => {
    expect(service.parse('Hello ${action1} this is a ${component1}.'))
      .toEqual(['Hello ', '${action1}', ' this is a ', '${component1}', '.']);

    expect(service.parse('${action1} this is a ${component1}.'))
      .toEqual(['${action1}', ' this is a ', '${component1}', '.']);

    expect(service.parse('${action1}${component1}${component2}'))
      .toEqual(['${action1}', '${component1}', '${component2}']);

    expect(service.parse('${action1}ttt${component2}'))
      .toEqual(['${action1}', 'ttt', '${component2}']);

    expect(service.parse('Start with ${action1} this is a ${component1}'))
      .toEqual(['Start with ', '${action1}', ' this is a ', '${component1}']);

    expect(service.parse('${action2}'))
      .toEqual(['${action2}']);

    expect(service.parse('${action2}${action1}'))
      .toEqual(['${action2}', '${action1}']);

    expect(service.parse('text'))
      .toEqual(['text']);

    expect(service.parse('Test1 ${action1}test2${action2}test3${action3}test4'))
      .toEqual(['Test1 ', '${action1}', 'test2', '${action2}', 'test3', '${action3}', 'test4']);

    done();
  });
});
