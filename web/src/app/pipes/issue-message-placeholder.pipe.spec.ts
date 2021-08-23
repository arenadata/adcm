import { IssueMessagePlaceholderPipe } from './issue-message-placeholder.pipe';

describe('IssueMessagePlaceholderPipe', () => {
  it('create an instance', () => {
    const pipe = new IssueMessagePlaceholderPipe();
    expect(pipe).toBeTruthy();
  });

  it('getting some names', () => {
    const pipe = new IssueMessagePlaceholderPipe();
    expect(pipe.transform('${component}')).toBe('component');
    expect(pipe.transform('${action}')).toBe('action');
  });
});
