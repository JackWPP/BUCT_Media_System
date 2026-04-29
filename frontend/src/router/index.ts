/**
 * Vue Router configuration - VCG Style Refactor
 */
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('../layouts/PublicLayout.vue'),
    meta: { requiresAuth: false },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/HomeView.vue'),
      },
      {
        path: 'gallery',
        name: 'Gallery',
        component: () => import('../views/GalleryView.vue'),
      },
      {
        path: 'photo/:id',
        name: 'PhotoDetail',
        component: () => import('../views/PhotoDetailView.vue'),
      },
    ],
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('../views/Upload.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/my-submissions',
    name: 'MySubmissions',
    component: () => import('../views/MySubmissions.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAuditor: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/admin/Dashboard.vue'),
        meta: { requiresAuth: true, requiresAuditor: true },
      },
      {
        path: 'review',
        name: 'PhotoReview',
        component: () => import('../views/admin/PhotoReview.vue'),
        meta: { requiresAuth: true, requiresAuditor: true },
      },
      {
        path: 'tags',
        name: 'TagManagement',
        component: () => import('../views/admin/TagManagement.vue'),
        meta: { requiresAuth: true, requiresAuditor: true },
      },
      {
        path: 'taxonomy',
        name: 'TaxonomyManagement',
        component: () => import('../views/admin/TaxonomyManagement.vue'),
        meta: { requiresAuth: true, requiresAuditor: true },
      },
      {
        path: 'import',
        name: 'PhotoImport',
        component: () => import('../views/admin/PhotoImport.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('../views/admin/UserManagement.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'settings',
        name: 'SystemSettings',
        component: () => import('../views/admin/SystemSettings.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'audit-logs',
        name: 'AuditLog',
        component: () => import('../views/admin/AuditLog.vue'),
        meta: { requiresAuth: true, requiresAdmin: true },
      },
      {
        path: 'database',
        name: 'DatabaseManagement',
        component: () => import('../views/admin/DatabaseManagement.vue'),
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

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false
  const requiresAdmin = to.meta.requiresAdmin === true
  const requiresAuditor = to.meta.requiresAuditor === true

  if (requiresAuth && !authStore.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }
  if (requiresAdmin && !authStore.isAdmin) {
    next(authStore.isAuditor ? '/admin/dashboard' : '/')
    return
  }
  if (requiresAuditor && !authStore.isAuditor) {
    next('/')
    return
  }
  if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
    return
  }
  next()
})

export default router
