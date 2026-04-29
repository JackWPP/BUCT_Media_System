export const SEASON_OPTIONS = [
    { label: '春季', value: 'Spring' },
    { label: '夏季', value: 'Summer' },
    { label: '秋季', value: 'Autumn' },
    { label: '冬季', value: 'Winter' },
]

export const CATEGORY_OPTIONS = [
    { label: '风光', value: 'Landscape' },
    { label: '人像', value: 'Portrait' },
    { label: '活动', value: 'Activity' },
    { label: '纪实', value: 'Documentary' },
]

export const CAMPUS_OPTIONS = [
    { label: '昌平校区', value: '昌平校区' },
    { label: '朝阳校区', value: '朝阳校区' },
]

export const SEASON_MAP: Record<string, string> = SEASON_OPTIONS.reduce((acc, curr) => {
    acc[curr.value] = curr.label
    return acc
}, {} as Record<string, string>)

export const CATEGORY_MAP: Record<string, string> = CATEGORY_OPTIONS.reduce((acc, curr) => {
    acc[curr.value] = curr.label
    return acc
}, {} as Record<string, string>)

export const CAMPUS_MAP: Record<string, string> = CAMPUS_OPTIONS.reduce((acc, curr) => {
    acc[curr.value] = curr.label
    return acc
}, {} as Record<string, string>)
