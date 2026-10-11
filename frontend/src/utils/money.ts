/**
 * 金额工具：全程整数分（架构 §3.1）。
 *
 * 唯一一次「元 → 分」换算发生在 parseYuanToCents（输入框提交时）；
 * 展示时 formatCents 用整数除法/取模还原，不引入任何浮点运算。
 */

/** 正数且最多两位小数的十进制字符串 */
const YUAN_PATTERN = /^\d+(\.\d{1,2})?$/

/**
 * 把用户输入的「元」字符串转换为「分」。
 * @returns 合法时返回正整数分；非法（空/负数/超过两位小数/非数字）时返回 null。
 */
export function parseYuanToCents(input: string): number | null {
  const trimmed = input.trim()
  if (!YUAN_PATTERN.test(trimmed)) {
    return null
  }
  const value = Number(trimmed)
  if (!Number.isFinite(value) || value <= 0) {
    return null
  }
  // 唯一换算点：Math.round 消除二进制浮点误差
  const cents = Math.round(value * 100)
  return cents > 0 ? cents : null
}

/** 把「分」格式化为两位小数的「元」字符串，例如 10000 → "100.00" */
export function formatCents(cents: number): string {
  const safe = Math.trunc(cents)
  const negative = safe < 0
  const abs = Math.abs(safe)
  const yuan = Math.floor(abs / 100)
  const fen = abs % 100
  const text = `${yuan}.${fen.toString().padStart(2, '0')}`
  return negative ? `-${text}` : text
}

/** 带正负号的净额展示：net>0 应收、net<0 应付 */
export function formatNet(cents: number): string {
  if (cents > 0) {
    return `+${formatCents(cents)}`
  }
  return formatCents(cents)
}
