<template>
  <Transition name="interpretation">
    <div v-if="interpretation && !interpretationHidden" class="search-interpretation">
      <div class="interpretation-header">
        <span v-if="isAiMethod" class="ai-badge">
          <span class="ai-sparkle">✨</span>
          AI 理解
        </span>
        <span v-else class="rule-badge">
          <span class="rule-icon">🔍</span>
          智能匹配
        </span>
        <n-button text size="tiny" class="dismiss-btn" @click="handleDismiss">
          <template #icon>
            <n-icon :component="CloseOutline" size="14" />
          </template>
        </n-button>
      </div>

      <div class="interpretation-tags">
        <TransitionGroup name="tag-pop" tag="div" class="tags-container">
          <span
            v-for="(tag, index) in displayTags"
            :key="tag.key"
            :style="{ transitionDelay: `${index * 80}ms` }"
            class="interpretation-tag"
            :class="[tag.type, { 'tag-removable': tag.removable }]"
          >
            <span class="tag-label">{{ tag.label }}</span>
            <span class="tag-value">{{ tag.value }}</span>
            <button
              v-if="tag.removable"
              class="tag-remove"
              @click.stop="handleRemoveTag(tag)"
            >
              ×
            </button>
          </span>
        </TransitionGroup>
      </div>

      <div v-if="interpretation.explanation" class="interpretation-explain">
        {{ interpretation.explanation }}
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NIcon } from 'naive-ui'
import { CloseOutline } from '@vicons/ionicons5'
import type { SearchInterpretation } from '../../types/photo'

const props = defineProps<{
  interpretation: SearchInterpretation | null
}>()

const emit = defineEmits<{
  (e: 'remove-facet', facetKey: string): void
  (e: 'remove-keyword', keyword: string): void
  (e: 'dismiss'): void
}>()

const interpretationHidden = ref(false)

watch(() => props.interpretation?.original_query, () => {
  interpretationHidden.value = false
})

const isAiMethod = computed(() => props.interpretation?.method === 'ai')

interface DisplayTag {
  key: string
  type: 'facet' | 'keyword'
  label: string
  value: string
  removable: boolean
}

const displayTags = computed<DisplayTag[]>(() => {
  if (!props.interpretation) return []

  const tags: DisplayTag[] = []

  for (const [facetKey, nodeValue] of Object.entries(props.interpretation.facet_filters)) {
    const facetNameMap: Record<string, string> = {
      season: '季节',
      campus: '校区',
      landmark: '地标',
      gallery_series: '专题',
      gallery_year: '年份',
      photo_type: '类型',
      building: '楼宇',
    }
    tags.push({
      key: `facet-${facetKey}`,
      type: 'facet',
      label: facetNameMap[facetKey] || facetKey,
      value: nodeValue,
      removable: true,
    })
  }

  for (const kw of props.interpretation.keywords) {
    tags.push({
      key: `kw-${kw}`,
      type: 'keyword',
      label: '关键词',
      value: kw,
      removable: true,
    })
  }

  return tags
})

function handleRemoveTag(tag: DisplayTag) {
  if (tag.type === 'facet') {
    const facetKey = tag.key.replace('facet-', '')
    emit('remove-facet', facetKey)
  } else {
    const keyword = tag.key.replace('kw-', '')
    emit('remove-keyword', keyword)
  }
}

function handleDismiss() {
  interpretationHidden.value = true
  emit('dismiss')
}
</script>

<style scoped>
.search-interpretation {
  margin-top: 8px;
  padding: 10px 14px;
  background: linear-gradient(135deg, rgba(230, 0, 18, 0.04), rgba(255, 255, 255, 0.9));
  border: 1px solid rgba(230, 0, 18, 0.12);
  border-radius: 10px;
  backdrop-filter: blur(8px);
}

.interpretation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.ai-badge,
.rule-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 10px;
}

.ai-badge {
  color: #8b5cf6;
  background: rgba(139, 92, 246, 0.1);
}

.rule-badge {
  color: #e60012;
  background: rgba(230, 0, 18, 0.08);
}

.ai-sparkle {
  font-size: 11px;
  animation: sparkle 1.5s ease-in-out infinite;
}

@keyframes sparkle {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.15); }
}

.rule-icon {
  font-size: 11px;
}

.dismiss-btn {
  opacity: 0.4;
  transition: opacity 0.2s;
}

.dismiss-btn:hover {
  opacity: 1;
}

.interpretation-tags {
  margin-bottom: 4px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.interpretation-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 14px;
  font-size: 12px;
  line-height: 1.5;
  transition: all 0.2s ease;
}

.interpretation-tag.facet {
  background: rgba(230, 0, 18, 0.08);
  color: #c4000f;
  border: 1px solid rgba(230, 0, 18, 0.15);
}

.interpretation-tag.keyword {
  background: rgba(0, 0, 0, 0.04);
  color: #555;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.interpretation-tag.tag-removable {
  cursor: pointer;
}

.interpretation-tag.tag-removable:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.interpretation-tag.facet.tag-removable:hover {
  background: rgba(230, 0, 18, 0.14);
}

.interpretation-tag.keyword.tag-removable:hover {
  background: rgba(0, 0, 0, 0.07);
}

.tag-label {
  font-weight: 500;
  opacity: 0.7;
  font-size: 11px;
}

.tag-value {
  font-weight: 600;
}

.tag-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  margin-left: 2px;
  border: none;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  color: inherit;
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
  padding: 0;
}

.interpretation-tag:hover .tag-remove {
  opacity: 1;
}

.tag-remove:hover {
  background: rgba(230, 0, 18, 0.2);
}

.interpretation-explain {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

/* Transitions */
.interpretation-enter-active {
  transition: all 0.3s ease-out;
}
.interpretation-leave-active {
  transition: all 0.2s ease-in;
}
.interpretation-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.interpretation-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.tag-pop-enter-active {
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.tag-pop-leave-active {
  transition: all 0.2s ease-in;
}
.tag-pop-enter-from {
  opacity: 0;
  transform: scale(0.6) translateY(4px);
}
.tag-pop-leave-to {
  opacity: 0;
  transform: scale(0.8);
}
</style>
