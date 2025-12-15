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

export const SEASON_MAP: Record<string, string> = SEASON_OPTIONS.reduce((acc, curr) => {
    acc[curr.value] = curr.label
    return acc
}, {} as Record<string, string>)

export const CATEGORY_MAP: Record<string, string> = CATEGORY_OPTIONS.reduce((acc, curr) => {
    acc[curr.value] = curr.label
    return acc
}, {} as Record<string, string>)
