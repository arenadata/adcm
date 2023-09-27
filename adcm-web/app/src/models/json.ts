export type JSONObject = { [x: string]: JSONValue };
export type JSONPrimitive = string | number | boolean | null;
export type JSONValue = JSONPrimitive | JSONObject | Array<JSONValue>;
