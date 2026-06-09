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

const CONTEST_YEAR_BY_EDITION: Record<string, string> = {
  第一届: '2018年',
  第二届: '2019年',
  第三届: '2020年',
  第四届: '2021年',
  第五届: '2022年',
  第六届: '2023年',
  第七届: '2024年',
  第八届: '2025年',
}

function parseContestEdition(photo: Photo | null | undefined) {
  const sourceText = [
    taxonomyValueName(photo?.classifications?.gallery_year),
    ...descriptionParts(photo),
    cleanText(photo?.filename),
  ].join(' ')

  const match = sourceText.match(/(第[一二三四五六七八九十0-9]+届)(?:获奖作品)?(?:昌平校区摄影大赛)?(?:获奖作品)?(?:（(20\d{2}年)）)?/)
  if (!match) return null

  return {
    edition: match[1],
    year: match[2] || CONTEST_YEAR_BY_EDITION[match[1]] || '',
  }
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
  const sourceType = taxonomyValueName(classifications.source_type)

  if (series === '昌平校区摄影大赛') {
    const parsed = parseContestEdition(photo)
    if (parsed?.edition && parsed.year) {
      return `${parsed.edition}昌平校区摄影大赛获奖作品（${parsed.year}）`
    }
    if (parsed?.edition) return `${parsed.edition}昌平校区摄影大赛获奖作品`
    return '昌平校区摄影大赛获奖作品'
  }

  if (series === '投稿作品') return '投稿作品'
  return series || sourceType || '未知'
}
