import { sortBy } from './arrayUtils.ts';

type ArrayItem = {
  id: number;
  name: string;
  numValue: number;
};

const array: ArrayItem[] = [
  {
    id: 1,
    name: 'Ketarol',
    numValue: 4,
  },
  {
    id: 2,
    name: 'Yamete kudasai',
    numValue: -3,
  },
  {
    id: 3,
    name: 'Deoxyribonucleic',
    numValue: 1,
  },
  {
    id: 4,
    name: 'Pithecanthropus',
    numValue: 5,
  },
  {
    id: 5,
    name: 'Ketarol',
    numValue: 3,
  },
];

describe('Array utils', () => {
  test('sort by name', () => {
    const result = sortBy(array, [(a, b) => a.name.localeCompare(b.name)]);

    expect(result).toStrictEqual([
      {
        id: 3,
        name: 'Deoxyribonucleic',
        numValue: 1,
      },
      {
        id: 1,
        name: 'Ketarol',
        numValue: 4,
      },
      {
        id: 5,
        name: 'Ketarol',
        numValue: 3,
      },
      {
        id: 4,
        name: 'Pithecanthropus',
        numValue: 5,
      },
      {
        id: 2,
        name: 'Yamete kudasai',
        numValue: -3,
      },
    ]);
  });

  test('sort by numValue and name', () => {
    const result = sortBy(array, [(a, b) => a.numValue - b.numValue, (a, b) => a.name.localeCompare(b.name)]);

    expect(result).toStrictEqual([
      {
        id: 2,
        name: 'Yamete kudasai',
        numValue: -3,
      },
      {
        id: 3,
        name: 'Deoxyribonucleic',
        numValue: 1,
      },
      {
        id: 5,
        name: 'Ketarol',
        numValue: 3,
      },
      {
        id: 1,
        name: 'Ketarol',
        numValue: 4,
      },
      {
        id: 4,
        name: 'Pithecanthropus',
        numValue: 5,
      },
    ]);
  });
});
