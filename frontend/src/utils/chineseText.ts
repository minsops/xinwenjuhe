export function usableChineseText(value?: string | null): string | undefined {
  const text = value?.trim();
  if (!text) return undefined;
  return hasReadableChinese(text) ? text : undefined;
}

export function hasReadableChinese(value: string): boolean {
  const cjkCount = [...value].filter((char) => char >= "\u4e00" && char <= "\u9fff").length;
  return cjkCount >= Math.max(2, Math.min(12, Math.floor(value.length / 16)));
}
