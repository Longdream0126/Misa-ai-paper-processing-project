"""词表与短语表：全部是纯文本数据，便于你按自己的领域继续补充。

这些列表是"可解释性"的来源：报告里每一条命中都会指出具体短语，
而不是给一个无法追溯的黑箱分数。
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# 英文
# --------------------------------------------------------------------------

EN_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "eg", "ie",
    "fig", "figs", "no", "nos", "inc", "ltd", "co", "corp", "dept", "est",
    "al", "approx", "cf", "ed", "eds", "vol", "pp", "p", "ch", "sec", "ref",
    "u.s", "u.k", "e.g", "i.e", "a.m", "p.m", "ph.d", "b.c", "a.d",
}

EN_CONTRACTIONS = {
    "it's", "that's", "there's", "what's", "who's", "he's", "she's", "here's",
    "how's", "let's", "where's", "when's", "why's",
    "they're", "we're", "you're", "i'm",
    "i've", "we've", "they've", "you've", "could've", "should've", "would've",
    "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",
    "can't", "couldn't", "shouldn't", "wouldn't", "haven't", "hasn't", "hadn't",
    "won't", "ain't", "mustn't", "needn't", "daren't",
    "i'll", "you'll", "we'll", "they'll", "he'll", "she'll", "it'll",
    "i'd", "you'd", "we'd", "they'd", "he'd", "she'd",
}

# 真正"口语/随手写"的词，学术写作与 AI 输出都很少用
EN_INFORMAL = {
    "gonna", "wanna", "kinda", "sorta", "gotta", "yeah", "yep", "nope", "ok",
    "okay", "lol", "hmm", "ugh", "wow", "cool", "stuff", "guy", "guys",
    "folks", "honestly", "anyway", "whatever", "meh", "oops", "alright",
    "dunno", "cuz", "tho", "tbh", "btw", "yikes", "hey", "hi",
}

# 句首话语标记（discourse markers）：AI 非常偏爱用它们组织段落
EN_TRANSITIONS = {
    "furthermore", "moreover", "additionally", "however", "therefore", "thus",
    "consequently", "nevertheless", "nonetheless", "overall", "ultimately",
    "indeed", "notably", "specifically", "similarly", "conversely", "meanwhile",
    "subsequently", "firstly", "secondly", "thirdly", "lastly",
    "in addition", "in conclusion", "in summary", "as such", "on the other hand",
    "first and foremost", "last but not least", "to sum up", "that said",
}

EN_FUNCTION_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "of", "at", "by", "for", "with",
    "about", "into", "through", "to", "from", "in", "on", "is", "are", "was",
    "were", "be", "been", "being", "am", "do", "does", "did", "have", "has",
    "had", "will", "would", "can", "could", "shall", "should", "may", "might",
    "must", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their", "this", "that",
    "these", "those", "not", "no", "so", "than", "then", "there", "here",
    "as", "just", "very", "too", "also", "up", "out", "off", "over", "under",
}

EN_NOMINAL_SUFFIXES = (
    "tion", "sion", "ment", "ness", "ity", "ance", "ence", "ization",
    "isation", "ency", "ancy", "ism",
)

# --------------------------------------------------------------------------
# 套话短语：(短语, 权重)。权重 1.0 = 强信号，0.3 = 弱信号（正常人也会用）。
# --------------------------------------------------------------------------

EN_CLICHES_STRONG = [
    "it is important to note", "it's important to note", "it is worth noting",
    "it's worth noting", "it is crucial to", "it's crucial to",
    "in today's fast-paced world", "in today's digital age",
    "in an ever-evolving", "in the ever-evolving", "the ever-evolving landscape",
    "in the realm of", "in the world of", "delve into", "delves into",
    "delving into", "dive into", "dive deeper", "let's dive in",
    "a testament to", "testament to", "navigate the complexities",
    "navigating the complexities", "navigate the landscape", "tapestry of",
    "a myriad of", "myriad of", "a plethora of", "plethora of",
    "in conclusion", "in summary", "to sum up", "to conclude",
    "plays a crucial role", "plays a vital role", "plays a pivotal role",
    "plays a significant role", "play a crucial role", "a pivotal role",
    "a crucial role in", "a vital role in", "shed light on", "sheds light on",
    "pave the way", "paves the way", "unlock the potential",
    "unlocking the potential", "harness the power", "harnessing the power",
    "at the end of the day", "it goes without saying", "needless to say",
    "when it comes to", "the fact that", "due to the fact that",
    "in order to", "a wide range of", "a wealth of", "an array of",
    "a double-edged sword", "the tip of the iceberg", "bridge the gap",
    "bridging the gap", "move the needle", "low-hanging fruit",
    "think outside the box", "circle back", "actionable insights",
    "key takeaways", "the key takeaway", "at its core", "the bottom line",
    "first and foremost", "last but not least", "as we navigate",
    "in an era of", "in an age of", "in this day and age",
    "it should be noted", "it can be argued", "embark on a journey",
    "a growing body of", "the landscape of", "the intersection of",
    "seamless integration", "seamlessly integrate", "robust framework",
    "holistic approach", "paradigm shift", "game-changer", "cutting-edge",
    "state-of-the-art", "best practices", "value proposition",
]

EN_CLICHES_WEAK = [
    "furthermore", "moreover", "additionally", "consequently", "nevertheless",
    "nonetheless", "therefore", "thus", "ultimately", "indeed", "notably",
    "utilize", "utilizes", "utilizing", "leverage", "leverages", "leveraging",
    "facilitate", "facilitates", "fostering", "foster", "fostered",
    "comprehensive", "innovative", "dynamic", "efficient", "effective",
    "crucial", "essential", "vital", "pivotal", "significant", "various",
    "numerous", "ensure", "ensures", "ensuring", "enhance", "enhances",
    "enhancing", "optimize", "optimizing", "streamline", "streamlining",
    "transformative", "meticulous", "meticulously", "nuanced", "multifaceted",
    "intricate", "underscore", "underscores", "underscoring", "realm",
    "landscape", "journey", "synergy", "synergies", "empower", "empowering",
    "elevate", "elevating", "revolutionize", "revolutionizing", "seamless",
    "seamlessly", "robust", "scalable", "sustainable", "proactive",
    "in essence", "by and large", "with that said", "that being said",
    "on the other hand", "in addition", "as a result", "in other words",
]

# 用正则捕捉可变的套话骨架
EN_CLICHE_PATTERNS = [
    (r"\b(plays?|played|play)\s+(a|an)\s+(crucial|vital|pivotal|significant|key|major)\s+role\b", 1.0),
    (r"\b(in|of)\s+the\s+(ever-evolving|rapidly\s+changing|fast-paced)\s+(landscape|world|environment)\b", 1.0),
    (r"\b(a|an)\s+(wide|broad|diverse)\s+(range|array|variety)\s+of\b", 0.5),
    (r"\bnot\s+only\s+.{0,40}?\s+but\s+also\b", 0.6),
    (r"\bit\s+is\s+(important|essential|crucial|vital)\s+to\b", 0.8),
    (r"\bthis\s+(highlights|underscores|demonstrates)\s+the\s+importance\b", 1.0),
    (r"\bby\s+(leveraging|utilizing|harnessing)\b", 0.7),
]

# --------------------------------------------------------------------------
# 中文
# --------------------------------------------------------------------------

ZH_CLICHES_STRONG = [
    "值得注意的是", "值得一提的是", "综上所述", "总而言之", "总的来说",
    "在当今社会", "在当今时代", "在这个信息爆炸的时代", "在这个快节奏的时代",
    "随着社会的发展", "随着科技的进步", "随着时代的发展",
    "具有重要意义", "具有深远意义", "有着重要意义", "起到了重要作用",
    "起到了至关重要的作用", "发挥着重要作用", "发挥着不可替代的作用",
    "不可忽视", "至关重要", "日益增长", "日益凸显", "愈发重要",
    "深入探讨", "深入剖析", "全面剖析", "多维度", "全方位", "深层次",
    "顶层设计", "赋能", "助力", "抓手", "闭环", "生态闭环", "深度融合",
    "持续发力", "高质量发展", "不断提升", "不断增强", "进一步推动",
    "由此可见", "显而易见", "毋庸置疑", "毫无疑问", "众所周知",
    "换言之", "与此同时", "首先，", "其次，", "再次，", "最后，",
    "让我们一起来", "让我们一起", "在这个", "综上所述，",
    "不仅丰富了", "不仅提高", "同时也为", "为...提供了",
]

ZH_CLICHES_WEAK = [
    "因此", "然而", "此外", "同时", "另外", "而且", "并且", "例如", "比如",
    "也就是说", "一方面", "另一方面", "不仅", "从而", "进而", "使得",
    "进行", "实现", "具有", "能够", "可以", "相关的", "相应的",
    "有效地", "极大地", "显著", "充分", "进一步", "不断", "大力",
    "打造", "构建", "赋予", "焕发", "彰显", "凸显", "践行", "诠释",
    "强大的", "丰富的", "独特的", "全新的",
]

ZH_CLICHE_PATTERNS = [
    (r"随着[^。，,\n]{0,18}(的|之)?(发展|普及|进步|兴起|推进)", 1.0),
    (r"在[^。，,\n]{0,10}(的)?(时代|背景下|大环境下)", 0.8),
    (r"起到[^。，,\n]{0,8}作用", 1.0),
    (r"越来越[^。，,\n]{0,8}(重要|普遍|明显|突出)", 0.7),
    (r"不仅[^。，,\n]{0,30}(而且|还|也)", 0.7),
    (r"为[^。，,\n]{0,12}(提供|带来|创造)了[^。，,\n]{0,12}(支持|保障|可能|机遇)", 0.8),
    (r"从[^。，,\n]{0,10}(来看|角度)[，,]", 0.6),
]

ZH_SCAFFOLD = [
    "首先", "其次", "再次", "最后", "第一", "第二", "第三",
    "一方面", "另一方面", "综上所述", "总之", "总而言之",
]

# 中文口语/个人化标记：真人写东西会带这些"毛边"
ZH_INFORMAL = [
    "挺", "其实", "感觉", "有点", "说实话", "老实说", "反正", "大概",
    "说不定", "好像", "差不多", "还行", "算了", "尴尬", "吐槽", "搞",
    "弄", "啥", "咋", "甭", "这事儿", "那事儿", "挺不错", "有点烦",
    "说白了", "说白了就是", "怎么说呢", "不知怎么", "硬是", "居然",
    "竟然", "偏要", "非得", "才怪", "呗", "啦", "嘛", "哎", "唉",
]

ZH_PARTICLES = "了吧啊呢嘛哦哈呀哪啦呗喽"

ZH_SENT_END = "。！？…!?"
ZH_CLAUSE_SEP = "，,、；;：:"

# --------------------------------------------------------------------------
# 元数据关键词（用于无扩展名/未知二进制文件的快速文本探测）
# --------------------------------------------------------------------------

METADATA_TAGS = [
    "Software", "CreatorTool", "Producer", "Creator", "Author", "Artist",
    "LastModifiedBy", "Application", "AppVersion", "Company", "c2pa",
    "JUMBF", "SynthID", "Made with Google", "DALL-E", "Midjourney",
    "Stable Diffusion", "Adobe Firefly", "ChatGPT", "OpenAI", "Copilot",
]
