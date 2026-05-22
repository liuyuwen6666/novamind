import axios from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const http = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000,
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg = error.response?.data?.message || error.response?.data?.msg || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default http