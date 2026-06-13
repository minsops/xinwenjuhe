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
  originalLanguage: "Original language",
  shortContentNotice: "This item only contains a short feed summary.",
  readFullOriginal: "Open original page",
  translate: "Translate to Chinese",
  translating: "Translating",
  original: "Show original",
  showChinese: "Show Chinese",
  summary: "Summary",
  basedOnReports: "Based on {count} reports",
  consensus: "Consensus",
  noConsensus: "No stable cross-source consensus yet.",
  disputes: "Disputes",
  noDisputes: "No contradictions detected.",
  blindSpots: "Blind Spots",
  blindSpotHelp: "Facts in this section were mentioned by only a small share of sources, so they need extra verification.",
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
  collectSourcesHelp: "Fetch the latest reports from configured RSS, API, and scraper sources.",
  clusterArticlesHelp: "Group newly collected reports into events and trigger analysis when needed.",
  collectHotEventsHelp: "Search multilingual Google News for high-heat events.",
  refreshCredibilityHelp: "Recalculate source credibility scores from transparency and press-freedom data.",
  submittingTask: "Submitting...",
  taskSubmitFailed: "Task submission failed. Check the backend service.",
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
  originalLanguage: "原文语言",
  shortContentNotice: "这条只包含来源摘要，正文较短。",
  readFullOriginal: "打开原始网页",
  translate: "翻译成中文",
  translating: "翻译中",
  original: "显示原文",
  showChinese: "显示中文",
  summary: "事件概要",
  basedOnReports: "基于 {count} 篇报道",
  consensus: "共识区",
  noConsensus: "尚无稳定的跨来源共识。",
  disputes: "争议区",
  noDisputes: "未检测到矛盾。",
  blindSpots: "盲区",
  blindSpotHelp: "这里指“报道盲区”：只有少数来源提到、覆盖不足的事实线索，需要重点核验，不代表一定为假。",
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
  collectSourcesHelp: "从已配置的 RSS、API 和网页来源抓取最新报道。",
  clusterArticlesHelp: "把新报道归入事件，并在需要时触发本站分析。",
  collectHotEventsHelp: "围绕热门事件搜索多语言 Google News 报道。",
  refreshCredibilityHelp: "按透明度、新闻自由度等数据重新计算来源可信度。",
  submittingTask: "正在提交...",
  taskSubmitFailed: "任务提交失败，请检查后端服务。",
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
  Argentina: "阿根廷",
  Bangladesh: "孟加拉国",
  Belarus: "白俄罗斯",
  Brazil: "巴西",
  Canada: "加拿大",
  China: "中国",
  France: "法国",
  Germany: "德国",
  India: "印度",
  Iran: "伊朗",
  Israel: "以色列",
  Italy: "意大利",
  Japan: "日本",
  Kazakhstan: "哈萨克斯坦",
  Kenya: "肯尼亚",
  Mexico: "墨西哥",
  Nepal: "尼泊尔",
  Nigeria: "尼日利亚",
  Pakistan: "巴基斯坦",
  Qatar: "卡塔尔",
  Russia: "俄罗斯",
  "Saudi Arabia": "沙特阿拉伯",
  "South Africa": "南非",
  "South Korea": "韩国",
  Spain: "西班牙",
  "Sri Lanka": "斯里兰卡",
  Taiwan: "中国台湾",
  Turkey: "土耳其",
  Ukraine: "乌克兰",
  "United Arab Emirates": "阿联酋",
  "United Kingdom": "英国",
  "United States": "美国",
  Venezuela: "委内瑞拉",
  Unknown: "未知国家"
};

const zhCategories: Record<string, string> = {
  conflict: "冲突",
  politics: "政治",
  economy: "经济",
  disaster: "灾害",
  technology: "科技",
  general: "综合",
  analysis: "分析"
};

const zhStatuses: Record<string, string> = {
  active: "进行中",
  archived: "已归档",
  merged: "已合并",
  split: "已拆分",
  pending_review: "待审核",
  approved: "已通过",
  rejected: "已拒绝"
};

const zhSourceNames: Record<string, string> = {
  "ada derana": "阿达德拉纳",
  "al arabiya": "阿拉比亚电视台",
  "al jazeera": "半岛电视台",
  allafrica: "全非洲新闻网",
  "anadolu agency": "阿纳多卢通讯社",
  ansa: "安莎社",
  "asahi shimbun": "朝日新闻",
  "associated press": "美联社",
  bbc: "英国广播公司",
  "bbc news": "英国广播公司",
  belta: "白通社",
  "central news agency": "中央社",
  "cbc news": "加拿大广播公司",
  clarin: "号角报",
  clarín: "号角报",
  cnn: "美国有线电视新闻网",
  dawn: "黎明报",
  "daily nation": "民族日报",
  "deutsche welle": "德国之声",
  dw: "德国之声",
  efe: "埃菲社",
  "el pais america": "国家报美洲版",
  "el país américa": "国家报美洲版",
  "el universal": "环球报",
  "el universal mexico": "墨西哥环球报",
  "folha de s.paulo": "圣保罗页报",
  "fox news": "福克斯新闻",
  "france 24": "法国24",
  "global times": "环球时报",
  haaretz: "国土报",
  "hindustan times": "印度斯坦时报",
  interfax: "国际文传电讯社",
  "islamic republic news agency": "伊朗伊斯兰共和国通讯社",
  irna: "伊朗伊斯兰共和国通讯社",
  kazinform: "哈通社",
  "kathmandu post": "加德满都邮报",
  "la nacion": "民族报",
  "la nación": "民族报",
  "le monde": "世界报",
  "mail & guardian": "邮报与卫报",
  ndtv: "新德里电视台",
  news24: "News24南非新闻网",
  nhk: "日本广播协会",
  npr: "美国国家公共广播电台",
  "o globo": "环球报",
  "premium times": "优质时报",
  "radio free europe radio liberty": "自由欧洲电台/自由电台",
  reuters: "路透社",
  "rfe/rl": "自由欧洲电台/自由电台",
  rt: "今日俄罗斯",
  tass: "塔斯社",
  telesur: "南方电视台",
  "the daily star": "每日星报",
  "the daily star bangladesh": "孟加拉每日星报",
  "the eastafrican": "东非人报",
  "the guardian": "卫报",
  "the guardian nigeria": "尼日利亚卫报",
  "the hindu": "印度教徒报",
  "the korea herald": "韩国先驱报",
  "the national": "国民报",
  "the new york times": "纽约时报",
  "trt world": "土耳其广播电视台国际频道",
  ukrinform: "乌克兰国家通讯社",
  "xinhua news agency": "新华社",
  "yonhap news agency": "韩联社",
  半岛电视台: "半岛电视台",
  朝日新闻: "朝日新闻",
  环球时报: "环球时报",
  韩联社: "韩联社",
  新华社: "新华社",
  中央社: "中央社"
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

export function formatCategory(category?: string | null): string {
  if (!category) return getUiText().analysis;
  const normalized = category.trim().toLowerCase().replace(/\s+/g, "_");
  return useChineseUi() ? zhCategories[normalized] ?? category : category;
}

export function formatStatus(status?: string | null): string {
  if (!status) return getUiText().unknown;
  const normalized = status.trim().toLowerCase().replace(/\s+/g, "_");
  return useChineseUi() ? zhStatuses[normalized] ?? status : status;
}

export function formatSourceName(name?: string | null, nameEn?: string | null): string {
  const primary = name?.trim() || nameEn?.trim();
  if (!primary) return getUiText().unknown;
  if (!useChineseUi()) return nameEn?.trim() || primary;
  const original = nameEn?.trim() || primary;
  const translated = zhSourceNames[primary.toLowerCase()] ?? zhSourceNames[original.toLowerCase()];
  if (!translated) {
    return nameEn && nameEn !== name ? `${name} / ${nameEn}` : primary;
  }
  return translated === original || translated === primary ? translated : `${translated} / ${original}`;
}

const zhLanguages: Record<string, string> = {
  auto: "自动识别",
  ar: "阿拉伯文",
  "ar-sa": "阿拉伯文",
  de: "德文",
  en: "英文",
  "en-us": "英文",
  "en-gb": "英文",
  es: "西班牙文",
  fa: "波斯文",
  fr: "法文",
  hi: "印地文",
  it: "意大利文",
  ja: "日文",
  ko: "韩文",
  multi: "多语种",
  pt: "葡萄牙文",
  ru: "俄文",
  tr: "土耳其文",
  uk: "乌克兰文",
  zh: "中文",
  "zh-cn": "中文",
  "zh-tw": "中文",
  "zh-hk": "中文"
};

export function formatLanguage(language?: string | null): string {
  if (!language) return getUiText().unknown;
  const normalized = language.toLowerCase();
  return zhLanguages[normalized] ?? zhLanguages[normalized.split("-")[0]] ?? language;
}
