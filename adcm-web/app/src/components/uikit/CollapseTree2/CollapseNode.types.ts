export type Node<T> = {
  data: T;
  key: string; // used as React.Key;
  children?: Node<T>[];
};
