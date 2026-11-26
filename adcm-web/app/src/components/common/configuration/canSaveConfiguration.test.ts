import { canSaveConfiguration } from './canSaveConfiguration';

const configVersions = [
  { id: 10, isCurrent: true },
  { id: 5, isCurrent: false },
  { id: 1, isCurrent: false },
];

describe('canSaveConfiguration', () => {
  test('returns false when no version is selected', () => {
    expect(canSaveConfiguration(null, configVersions)).toBe(false);
  });

  test('returns false when Current version is selected', () => {
    expect(canSaveConfiguration(10, configVersions)).toBe(false);
  });

  test('returns true in Editing mode', () => {
    expect(canSaveConfiguration(0, configVersions)).toBe(true);
  });

  test('returns true when a historical version is selected', () => {
    expect(canSaveConfiguration(5, configVersions)).toBe(true);
    expect(canSaveConfiguration(1, configVersions)).toBe(true);
  });
});
