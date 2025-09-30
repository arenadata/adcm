export type Node<T> = {
  data: T;
  index: number;
  key: string; // used as React.Key;
  children?: Node<T>[];
};
