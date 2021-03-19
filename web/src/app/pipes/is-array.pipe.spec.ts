import { IsArrayPipe } from './is-array.pipe';

describe('IsArrayPipe', () => {
  it('create an instance', () => {
    const pipe = new IsArrayPipe();
    expect(pipe).toBeTruthy();
  });
});
