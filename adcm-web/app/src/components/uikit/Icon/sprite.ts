export const allowIconsNames = [
  //
  'eye',
  'eye-crossed',
] as const;

export type IconsNames = (typeof allowIconsNames)[number];
