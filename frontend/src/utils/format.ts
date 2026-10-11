/** 日期时间展示工具（不引入 dayjs 等额外依赖）。 */

function pad(n: number): string {
  return n.toString().padStart(2, '0')
}

/** 输出 yyyy-MM-dd HH:mm；无法解析时原样返回 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`
}

/** 输出 yyyy-MM-dd；无法解析时原样返回 */
export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
