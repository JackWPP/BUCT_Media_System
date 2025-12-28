/**
 * v-permission 权限指令
 * 
 * 根据用户角色控制元素的显示/隐藏。
 * 
 * 使用方法:
 * - v-permission="'admin'" - 仅管理员可见
 * - v-permission="['admin', 'auditor']" - 管理员或审核员可见
 */
import type { Directive, DirectiveBinding } from 'vue'
import { useAuthStore } from '../stores/auth'
import type { UserRole } from '../types/user'

export const vPermission: Directive = {
    mounted(el: HTMLElement, binding: DirectiveBinding<UserRole | UserRole[]>) {
        checkPermission(el, binding)
    },
    updated(el: HTMLElement, binding: DirectiveBinding<UserRole | UserRole[]>) {
        checkPermission(el, binding)
    },
}

function checkPermission(el: HTMLElement, binding: DirectiveBinding<UserRole | UserRole[]>) {
    const authStore = useAuthStore()
    const requiredRoles = binding.value

    if (!requiredRoles) {
        return
    }

    const hasPermission = authStore.hasRole(requiredRoles)

    if (!hasPermission) {
        // 移除元素
        el.parentNode?.removeChild(el)
    }
}

export default vPermission
