import type { Photo } from '../types/photo'
import { taxonomyValueName } from '../types/photo'

const META_PART_PATTERNS = [
  /^作者[:：]/,
  /^序号[:：]/,
  /^排名[:：]/,
  /^评分[:：]/,
  /^第[一二三四五六七八九十0-9]+届.*摄影大赛/,
  /^(风光类|纪实类|建筑楼宇|校区设施|自然生态|优秀奖|一等奖|二等奖|三等奖|网络人气奖)$/,
]

function cleanText(value: string | null | undefined) {
  return (value || '').trim()
}

export function descriptionParts(photo: Photo | null | undefined) {
  return cleanText(photo?.description)
    .split('|')
    .map((part) => part.trim())
    .filter(Boolean)
}

function cleanAuthor(value: string | null | undefined) {
  return cleanText(value)
    .replace(/^作者[:：]\s*/, '')
    .replace(/[|].*$/, '')
    .replace(/\s*(?:（教师）|（学生）|（宣传部）|\(教师\)|\(学生\)|\(宣传部\))\s*$/, '')
    .trim()
}

function splitLegacyTitleAuthor(part: string) {
  const match = part.match(/^(.+?)\s*[-－—]\s*(.+)$/)
  if (!match) return null
  const title = cleanText(match[1])
  const author = cleanAuthor(match[2])
  if (!title || !author) return null
  return { title, author }
}

export function parsePhotoTitle(photo: Photo | null | undefined) {
  const parts = descriptionParts(photo)
  const titlePart = parts.find((part) => !META_PART_PATTERNS.some((pattern) => pattern.test(part)))
  if (!titlePart) return ''
  const legacy = splitLegacyTitleAuthor(titlePart)
  return (legacy?.title || titlePart.replace(/^作品名称[:：]\s*/, '')).trim()
}

export function parsePhotoAuthor(photo: Photo | null | undefined) {
  const parts = descriptionParts(photo)
  const explicit = parts.find((part) => /^作者[:：]/.test(part))
  if (explicit) return cleanAuthor(explicit)

  for (const part of parts) {
    const legacy = splitLegacyTitleAuthor(part)
    if (legacy?.author) return legacy.author
  }

  return ''
}

export function displayPhotoTitle(photo: Photo | null | undefined) {
  if (!photo) return '未知'
  return cleanText(photo.title) || parsePhotoTitle(photo) || photo.filename.replace(/\.[^.]+$/, '')
}

export function displayPhotoAuthor(photo: Photo | null | undefined) {
  if (!photo) return '未知'
  return cleanText(photo.author) || parsePhotoAuthor(photo) || '未知'
}

export function formatPhotoSource(photo: Photo | null | undefined) {
  const classifications = photo?.classifications || {}
  const series = taxonomyValueName(classifications.gallery_series)
  const galleryYear = taxonomyValueName(classifications.gallery_year)
  const sourceType = taxonomyValueName(classifications.source_type)

  if (series === '昌平校区摄影大赛') {
    const match = galleryYear.match(/^(第.+?届)获奖作品（(.+?)）$/)
    if (match) return `${match[1]}昌平校区摄影大赛获奖作品（${match[2]}）`
    return galleryYear || '昌平校区摄影大赛获奖作品'
  }

  if (series === '投稿作品') return '投稿作品'
  return series || sourceType || '未知'
}
