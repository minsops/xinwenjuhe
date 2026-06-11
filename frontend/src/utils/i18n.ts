const en = {
  searchEvents: "Search events",
  news: "News",
  analysis: "Analysis",
  loadingAnalysis: "Loading analysis...",
  allRegions: "All regions",
  allCategories: "All categories",
  conflict: "Conflict",
  politics: "Politics",
  economy: "Economy",
  disaster: "Disaster",
  technology: "Technology",
  heat: "Heat",
  latest: "Latest",
  noArticle: "No article selected.",
  source: "Source",
  sourceAgency: "News outlet",
  sourceCountry: "Country",
  sourceRegion: "Region",
  sourceLanguage: "Language",
  credibility: "Credibility",
  originalArticle: "Original article",
  translatedVersion: "Chinese translation",
  shortContentNotice: "This item only contains a short feed summary.",
  readFullOriginal: "Open original page",
  translate: "Translate to Chinese",
  translating: "Translating",
  original: "Original",
  summary: "Summary",
  basedOnReports: "Based on {count} reports",
  consensus: "Consensus",
  noConsensus: "No stable cross-source consensus yet.",
  disputes: "Disputes",
  noDisputes: "No contradictions detected.",
  blindSpots: "Blind Spots",
  noBlindSpots: "No low-coverage facts identified.",
  narrativeFrames: "Narrative Frames",
  noFrames: "Frame analysis has not run yet.",
  timeline: "Timeline",
  noTimeline: "No timestamped facts yet.",
  sourceGraph: "Source Graph",
  noSourceGraph: "No source relationships yet.",
  reportedLinks: "reported links",
  conflictLinks: "conflict links",
  reports: "reports",
  sources: "sources",
  regions: "regions",
  languages: "languages",
  sourceOrder: "Source order",
  byCredibility: "Credibility",
  byRegion: "Region",
  fullReportsFirst: "Full reports first",
  operationsTitle: "Background tasks",
  operationsSubtitle: "Collection, clustering, and source scoring.",
  queueDepth: "Queue",
  collectSources: "Collect sources",
  clusterArticles: "Cluster articles",
  collectHotEvents: "Collect hot events",
  refreshCredibility: "Refresh credibility",
  queuedTask: "Queued",
  recentTasks: "Recent tasks",
  noRecentTasks: "No recent tasks.",
  hotStatus: "Hot",
  activeStatus: "Active",
  unknown: "Unknown"
};

export type UiText = typeof en;

const zh: UiText = {
  searchEvents: "搜索事件",
  news: "新闻",
  analysis: "分析",
  loadingAnalysis: "正在加载分析...",
  allRegions: "全部地区",
  allCategories: "全部分类",
  conflict: "冲突",
  politics: "政治",
  economy: "经济",
  disaster: "灾害",
  technology: "科技",
  heat: "热度",
  latest: "最新",
  noArticle: "未选择文章。",
  source: "原始链接",
  sourceAgency: "新闻机构",
  sourceCountry: "所属国家",
  sourceRegion: "地区",
  sourceLanguage: "语言",
  credibility: "可信度",
  originalArticle: "原文报道",
  translatedVersion: "中文翻译",
  shortContentNotice: "这条只包含来源摘要，正文较短。",
  readFullOriginal: "打开原始网页",
  translate: "翻译成中文",
  translating: "翻译中",
  original: "切回原文",
  summary: "事件概要",
  basedOnReports: "基于 {count} 篇报道",
  consensus: "共识区",
  noConsensus: "尚无稳定的跨来源共识。",
  disputes: "争议区",
  noDisputes: "未检测到矛盾。",
  blindSpots: "盲区",
  noBlindSpots: "未发现低覆盖事实。",
  narrativeFrames: "叙事框架",
  noFrames: "叙事框架分析尚未运行。",
  timeline: "时间轴",
  noTimeline: "暂无带时间的事实片段。",
  sourceGraph: "来源图谱",
  noSourceGraph: "暂无来源关系。",
  reportedLinks: "报道关系",
  conflictLinks: "冲突关系",
  reports: "报道",
  sources: "来源",
  regions: "地区",
  languages: "语言",
  sourceOrder: "来源排序",
  byCredibility: "可信度",
  byRegion: "地区",
  fullReportsFirst: "完整报道优先",
  operationsTitle: "后台任务",
  operationsSubtitle: "采集新闻、聚类文章、刷新来源可信度。",
  queueDepth: "队列",
  collectSources: "采集全部来源",
  clusterArticles: "聚类新文章",
  collectHotEvents: "补采热门事件",
  refreshCredibility: "刷新来源可信度",
  queuedTask: "已加入队列",
  recentTasks: "最近任务",
  noRecentTasks: "暂无最近任务。",
  hotStatus: "热门",
  activeStatus: "进行中",
  unknown: "未知"
};

export function getUiText(): UiText {
  return zh;
}

export function formatMessage(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce((text, [key, value]) => text.replace(`{${key}}`, String(value)), template);
}

const zhRegions: Record<string, string> = {
  north_america: "北美",
  europe: "欧洲",
  east_asia: "东亚",
  middle_east: "中东",
  south_asia: "南亚",
  africa: "非洲",
  latin_america: "拉美",
  russia_cis: "俄罗斯/独联体",
  unknown: "未知地区"
};

const enRegions: Record<string, string> = {
  north_america: "North America",
  europe: "Europe",
  east_asia: "East Asia",
  middle_east: "Middle East",
  south_asia: "South Asia",
  africa: "Africa",
  latin_america: "Latin America",
  russia_cis: "Russia/CIS",
  unknown: "Unknown region"
};

const zhCountries: Record<string, string> = {
  "United Kingdom": "英国",
  Qatar: "卡塔尔",
  Iran: "伊朗",
  "United States": "美国",
  China: "中国",
  Russia: "俄罗斯",
  Turkey: "土耳其",
  Germany: "德国",
  France: "法国",
  Japan: "日本",
  "South Korea": "韩国",
  India: "印度",
  Unknown: "未知国家"
};

function useChineseUi(): boolean {
  return true;
}

export function formatRegion(region?: string | null): string {
  const key = region || "unknown";
  const labels = useChineseUi() ? zhRegions : enRegions;
  return labels[key] ?? key;
}

export function formatCountry(country?: string | null): string {
  if (!country) return getUiText().unknown;
  return useChineseUi() ? zhCountries[country] ?? country : country;
}
