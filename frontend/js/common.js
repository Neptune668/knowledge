/**
 * 知识库管理平台前端 —— 公共工具函数
 * 纯原生 JavaScript，无依赖
 */

// ===== 基础配置 =====
// 后端 API 地址
// - 生产部署（Nginx 同源托管前端 + 反代后端）：用相对路径 '/api'
// - 本机测试（前端静态服务器 + 后端独立端口）：改为 'http://localhost:8000/api'
const BASE_URL = '/api';

// ===== Token 与登录态管理 =====

function getToken() {
  return localStorage.getItem('access_token') || '';
}

function getUserInfo() {
  try {
    return JSON.parse(localStorage.getItem('user_info') || 'null');
  } catch (e) {
    return null;
  }
}

function getPermissions() {
  try {
    return JSON.parse(localStorage.getItem('permissions') || '[]');
  } catch (e) {
    return [];
  }
}

// 登录态守卫：无 token 跳转登录页
function requireLogin() {
  if (!getToken()) {
    location.href = 'login.html';
    return false;
  }
  return true;
}

// 退出登录
function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_info');
  localStorage.removeItem('permissions');
  location.href = 'login.html';
}

// ===== 权限控制 =====

function hasPermission(code) {
  const perms = getPermissions();
  return perms.includes(code);
}

// 页面加载时根据 data-perm 属性控制元素显隐
function applyPermission() {
  document.querySelectorAll('[data-perm]').forEach((el) => {
    const code = el.getAttribute('data-perm');
    if (code && !hasPermission(code)) {
      el.style.display = 'none';
    }
  });
}

// ===== HTTP 请求封装 =====

async function request(url, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
  };
  // 有 body 且未手动指定 Content-Type 时才自动加（文件上传除外）
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let resp;
  try {
    resp = await fetch(BASE_URL + url, { ...options, headers });
  } catch (e) {
    toast('网络错误，请检查后端服务是否启动', 'error');
    throw e;
  }

  // 401 未登录
  if (resp.status === 401) {
    localStorage.removeItem('access_token');
    toast('登录已过期，请重新登录', 'error');
    setTimeout(() => (location.href = 'login.html'), 800);
    throw new Error('未登录');
  }
  // 403 无权限
  if (resp.status === 403) {
    toast('无操作权限', 'error');
    throw new Error('无权限');
  }
  // 422 参数错误
  if (resp.status === 422) {
    toast('参数校验失败', 'error');
    throw new Error('参数错误');
  }
  // 500
  if (resp.status >= 500) {
    toast('服务器错误', 'error');
    throw new Error('服务器错误');
  }

  const data = await resp.json();
  return data;
}

const http = {
  get: (url) => request(url, { method: 'GET' }),
  post: (url, body) => request(url, { method: 'POST', body: JSON.stringify(body) }),
  put: (url, body) => request(url, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (url, body) => request(url, { method: 'DELETE', body: JSON.stringify(body) }),
};

// ===== 提示组件（简易 toast）=====

function toast(message, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ===== 通用工具 =====

// 格式化时间（ISO 字符串 → 本地可读）
function formatTime(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// 转义 HTML（防 XSS）
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

// 获取 URL 查询参数
function getQueryParam(name) {
  const params = new URLSearchParams(location.search);
  return params.get(name);
}
