export type JSONObject = { [x: string]: JSONValue };
export type JSONPrimitive = string | number | boolean | null | undefined;
export type JSONValue = JSONPrimitive | JSONObject | Array<JSONValue>;

export function isPrimitiveValueSet(value: JSONPrimitive): value is Exclude<JSONPrimitive, null | undefined> {
  return value !== undefined && value !== null;
}

export function isValueSet(value: JSONValue): value is Exclude<JSONValue, null | undefined> {
  return value !== undefined && value !== null;
}
