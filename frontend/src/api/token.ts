/**
 * token 存储：内存优先 + sessionStorage 兜底。
 *
 * 取舍说明（V1）：
 * - 不使用 localStorage：localStorage 为持久存储，一旦发生 XSS，攻击者可在任意时间读取
 *   并长期盗用 token。sessionStorage 随标签页/会话结束而清空，暴露窗口更小。
 * - 采用「内存变量为主 + sessionStorage 为辅」：内存变量保证同一页面内读写最快；
 *   sessionStorage 用于页面刷新后恢复（否则刷新即登出，体验不可接受）。
 * - 副作用：关闭标签页即需重新登录，这是 V1 有意接受的代价。
 *
 * 注意：本模块不依赖 axios / 其他业务模块，作为最底层依赖，避免循环引用。
 */
const TOKEN_KEY = 'splitway_token'

let memoryToken: string | null = readStoredToken()

function readStoredToken(): string | null {
  try {
    return window.sessionStorage.getItem(TOKEN_KEY)
  } catch {
    // 隐私模式等场景下 sessionStorage 可能抛异常，降级为纯内存
    return null
  }
}

export function getToken(): string | null {
  return memoryToken
}

export function setToken(token: string): void {
  memoryToken = token
  try {
    window.sessionStorage.setItem(TOKEN_KEY, token)
  } catch {
    // 忽略写入失败：内存中仍持有 token，本次会话可用
  }
}

export function clearToken(): void {
  memoryToken = null
  try {
    window.sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    // 忽略
  }
}
