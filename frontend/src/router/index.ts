/**
 * Vue Router 配置
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// 路由配置
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    name: 'Gallery',
    component: () => import('../views/Gallery.vue'),
    meta: { requiresAuth: false },  // 普通用户可直接访问
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('../views/Upload.vue'),
    meta: { requiresAuth: true },  // 上传需要登录
  },
  // 后台管理路由
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: '',
        redirect: '/admin/review',
      },
      {
        path: 'review',
        name: 'PhotoReview',
        component: () => import('../views/admin/PhotoReview.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'tags',
        name: 'TagManagement',
        component: () => import('../views/admin/TagManagement.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'import',
        name: 'PhotoImport',
        component: () => import('../views/admin/PhotoImport.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
  },
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局前置守卫
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false
  const requiresAdmin = to.meta.requiresAdmin === true

  if (requiresAuth && !authStore.isAuthenticated) {
    // 需要认证但未登录，跳转到登录页
    next({
      path: '/login',
      query: { redirect: to.fullPath },
    })
  } else if (requiresAdmin && authStore.user?.role !== 'admin') {
    // 需要管理员权限但不是管理员
    next('/')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    // 已登录用户访问登录页，跳转到首页
    next('/')
  } else {
    // 其他情况，正常访问
    next()
  }
})

export default router
