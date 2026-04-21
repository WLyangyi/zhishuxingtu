import axios, { AxiosError } from 'axios'
import { useNotificationStore } from '@/stores/notification'

export interface ApiError {
  message: string
  code?: string
  status?: number
}

interface ErrorData {
  message?: string
  detail?: string
}

const STATUS_MESSAGES: Record<number, string> = {
  401: '登录已过期，请重新登录',
  403: '没有权限执行此操作',
  404: '请求的资源不存在',
  500: '服务器错误，请稍后重试',
  502: '网关错误，请稍后重试',
  503: '服务暂不可用，请稍后重试',
}

const NETWORK_ERROR_CODES: Record<string, string> = {
  ECONNABORTED: '请求超时，请检查网络连接',
  ERR_NETWORK: '网络连接失败，请检查网络设置',
  ERR_CANCELED: '请求已取消',
}

function extractMessageFromData(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null

  const errorData = data as ErrorData

  if (typeof errorData.message === 'string' && errorData.message.trim()) {
    return errorData.message.trim()
  }

  if (typeof errorData.detail === 'string' && errorData.detail.trim()) {
    return errorData.detail.trim()
  }

  return null
}

export function parseApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError<ErrorData>
    const status = axiosErr.response?.status
    const responseData = axiosErr.response?.data

    const extractedMessage = extractMessageFromData(responseData)
    if (extractedMessage) {
      return {
        message: extractedMessage,
        status,
        code: axiosErr.code,
      }
    }

    if (status && STATUS_MESSAGES[status]) {
      return {
        message: STATUS_MESSAGES[status],
        status,
        code: axiosErr.code,
      }
    }

    if (axiosErr.code && NETWORK_ERROR_CODES[axiosErr.code]) {
      return {
        message: NETWORK_ERROR_CODES[axiosErr.code],
        code: axiosErr.code,
      }
    }

    if (axiosErr.message && !axiosErr.response) {
      return {
        message: '网络连接失败，请检查网络设置',
        code: axiosErr.code,
      }
    }

    return {
      message: '请求失败，请稍后重试',
      status,
      code: axiosErr.code,
    }
  }

  if (error instanceof Error) {
    return { message: error.message }
  }

  if (typeof error === 'string') {
    return { message: error }
  }

  return { message: '未知错误，请稍后重试' }
}

export function handleApiError(
  error: unknown,
  defaultTitle: string = '操作失败',
  defaultMessage: string = '请稍后重试'
): void {
  const apiError = parseApiError(error)

  if (apiError.status === 401) {
    return
  }

  const notification = useNotificationStore()
  notification.error(defaultTitle, apiError.message || defaultMessage)
}
