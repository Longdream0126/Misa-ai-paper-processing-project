"""Internationalisation for Misa's AI Paper Processing Project.

English is the source language; every user-visible string in the web UI and the
CLI goes through :func:`t` so the whole interface can switch language at runtime.

Supported locales: ``en``, ``zh-CN``, ``zh-TW``, ``ja``.
"""

from __future__ import annotations

import locale as _locale
import os

LOCALES = ("en", "zh-CN", "zh-TW", "ja")
LOCALE_NAMES = {
    "en": "English",
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
    "ja": "日本語",
}
DEFAULT_LOCALE = "en"

_ALIASES = {
    "en": "en", "en-us": "en", "en-gb": "en", "en_us": "en",
    "zh": "zh-CN", "zh-cn": "zh-CN", "zh-hans": "zh-CN", "zh_cn": "zh-CN",
    "zh-tw": "zh-TW", "zh-hk": "zh-TW", "zh-hant": "zh-TW", "zh_tw": "zh-TW",
    "ja": "ja", "ja-jp": "ja", "jp": "ja",
}


def normalize(code: str | None) -> str | None:
    if not code:
        return None
    key = code.strip().replace("_", "-").lower()
    if key in _ALIASES:
        return _ALIASES[key]
    base = key.split("-")[0]
    return _ALIASES.get(base)


def system_locale() -> str | None:
    """Locale from MISA_LANG, then the OS UI language."""
    env = os.environ.get("MISA_LANG")
    hit = normalize(env)
    if hit:
        return hit
    try:
        lang = _locale.getlocale()[0] or _locale.getdefaultlocale()[0]
    except (ValueError, AttributeError):
        lang = None
    return normalize(lang)


def resolve(explicit: str | None = None) -> str:
    return normalize(explicit) or system_locale() or DEFAULT_LOCALE


# (key, en, zh-CN, zh-TW, ja)
_ROWS: list[tuple[str, str, str, str, str]] = [
    # ---------------------------------------------------------------- app
    ("app.name", "Misa's AI Paper Processing Project",
     "Misa's AI Paper Processing Project", "Misa's AI Paper Processing Project",
     "Misa's AI Paper Processing Project"),
    ("app.tagline", "AI-writing signals, checked locally", "AI 写作痕迹 · 本地检查",
     "AI 寫作痕跡 · 本地檢查", "AI 文章の痕跡をローカルで検査"),
    ("app.tagline_short", "AI-writing signals, checked locally", "AI 写作痕迹 · 本地检查",
     "AI 寫作痕跡 · 本地檢查", "AI 文章の痕跡をローカルで検査"),
    ("local.badge", "Local only", "本地运行", "本地執行", "ローカルのみ"),
    ("app.made_by", "Made by Misa", "本项目由 Misa 制作", "本專案由 Misa 製作", "Misa 制作"),
    ("app.footer_local", "Zero dependencies · fully local · nothing uploaded",
     "零依赖 · 纯本地 · 不上传文本", "零依賴 · 純本地 · 不上傳文字", "依存ゼロ · 完全ローカル · 送信なし"),
    ("app.footer_caveat",
     "The score is a heuristic statistic — not evidence of authorship.",
     "分数是启发式统计量，不能作为学术不端或版权归属的判决依据",
     "分數是啟發式統計量，不能作為學術不端或版權歸屬的判決依據",
     "スコアはヒューリスティックな統計値で、著作権や不正の判断根拠にはなりません"),
    ("app.disclaimer",
     "This score is a heuristic statistic: it measures similarity to default AI writing style, "
     "not who wrote it. Genre and register change the number as much as the author does. No detection "
     "result should be the sole basis for an academic-integrity, copyright or legal decision.",
     "本分数是启发式统计量，衡量的是「文本与 AI 默认文风的相似度」，不是作者身份判定。"
     "同一段文字换个题裁、语域或语言，分数就会变。任何检测结论都不应作为学术不端、"
     "版权归属或法律判断的唯一依据。",
     "本分數是啟發式統計量，衡量的是「文字與 AI 預設文風的相似度」，不是作者身分判定。"
     "同一段文字換個題材、語域或語言，分數就會變。任何檢測結論都不應作為學術不端、"
     "版權歸屬或法律判斷的唯一依據。",
     "このスコアは「AI の既定の文体にどれだけ似ているか」を測るヒューリスティックな統計値で、"
     "誰が書いたかの判定ではありません。題材・言語・レジスターが変われば数値も変わります。"
     "学術不正・著作権・法的判断の唯一の根拠にしないでください。"),

    # ---------------------------------------------------------------- nav
    ("tab.analyze", "Analyze", "分析", "分析", "分析"),
    ("tab.humanize", "Rewrite", "改写", "改寫", "書き換え"),
    ("tab.marks", "Invisible marks", "隐形标记", "隱形標記", "不可視マーク"),
    ("tab.watermark", "Watermark", "水印", "浮水印", "電子透かし"),
    ("nav.language", "Language", "语言", "語言", "言語"),

    # ---------------------------------------------------------------- analyze
    ("analyze.pane", "Text to check", "待检查文本", "待檢查文字", "検査する文章"),
    ("analyze.sample", "Load a sample…", "载入示例…", "載入範例…", "サンプルを読み込む…"),
    ("analyze.count", "{n} chars", "{n} 字", "{n} 字", "{n} 文字"),
    ("analyze.placeholder",
     "Paste the text you want to check. Chinese and English both work; longer text gives a steadier score.",
     "把要检查的文字粘在这里。中英文都支持；越长的文本分数越稳。",
     "把要檢查的文字貼在這裡。中英文都支援；越長的文字分數越穩。",
     "調べたい文章を貼り付けてください。中国語・英語に対応。長いほど安定します。"),
    ("analyze.run", "Analyze", "开始分析", "開始分析", "分析する"),
    ("analyze.clear", "Clear", "清空", "清空", "クリア"),
    ("analyze.hint", "Ctrl + Enter", "Ctrl + Enter", "Ctrl + Enter", "Ctrl + Enter"),
    ("analyze.empty",
     "Nothing yet. Paste some text on the left, then hit Analyze.",
     "还没有结果。左边贴一段文字，点「开始分析」。",
     "還沒有結果。左邊貼一段文字，點「開始分析」。",
     "まだ結果がありません。左に文章を貼り、「分析する」を押してください。"),

    # ---------------------------------------------------------------- result
    ("result.band.human", "Looks human", "很像人写的", "很像人寫的", "人間らしい"),
    ("result.band.lean_human", "Leaning human", "偏人类文风", "偏人類文風", "やや人間寄り"),
    ("result.band.mixed", "Mixed / unclear", "混合 / 说不准", "混合 / 說不準", "混合・判断不能"),
    ("result.band.lean_ai", "Leaning AI", "偏 AI 文风", "偏 AI 文風", "やや AI 寄り"),
    ("result.band.ai", "Strongly AI-like", "高度 AI 化", "高度 AI 化", "かなり AI 的"),
    ("result.conf.high", "high confidence", "可信度 较高", "可信度 較高", "信頼度：高"),
    ("result.conf.medium", "medium confidence", "可信度 中等", "可信度 中等", "信頼度：中"),
    ("result.conf.low", "low confidence", "可信度 较低", "可信度 較低", "信頼度：低"),
    ("result.conf.very_low", "very low confidence", "可信度 很低", "可信度 很低", "信頼度：ごく低"),
    ("result.lang.en", "English", "英文", "英文", "英語"),
    ("result.lang.zh", "Chinese", "中文", "中文", "中国語"),
    ("result.calibrated", "custom calibration", "自定义标定", "自訂標定", "独自キャリブレーション"),
    ("result.features", "Feature breakdown", "特征明细", "特徵明細", "特徴の内訳"),
    ("result.features_hint", "value · weight (longer bar = more AI-like)",
     "数值 · 权重（条越长越像 AI）", "數值 · 權重（條越長越像 AI）",
     "値 · 重み（バーが長いほど AI 的）"),
    ("result.diagnosis", "Findings", "诊断", "診斷", "所見"),
    ("result.sentences", "Most AI-like sentences", "最像 AI 的句子", "最像 AI 的句子", "AI らしい文"),
    ("result.sentences_hint", "Click to select it in the editor",
     "点击可在左侧选中", "點擊可在左側選取", "クリックで本文内を選択"),
    ("result.no_features", "Text too short — no usable features.",
     "文本太短，没有可用的特征。", "文字太短，沒有可用的特徵。", "短すぎて使える特徴がありません。"),
    ("result.left", "human", "像人写的", "像人寫的", "人間側"),
    ("result.middle", "unclear", "说不准", "說不準", "不明"),
    ("result.right", "AI", "像 AI", "像 AI", "AI 側"),
    ("result.ai_side", "AI", "AI", "AI", "AI"),
    ("result.human_side", "human", "人", "人", "人間"),

    # ---------------------------------------------------------------- stats
    ("stat.units", "{n} {unit}", "{n} {unit}", "{n} {unit}", "{n} {unit}"),
    ("stat.sentences", "{n} sentences", "{n} 句", "{n} 句", "{n} 文"),
    ("stat.paragraphs", "{n} paragraphs", "{n} 段", "{n} 段", "{n} 段落"),
    ("stat.avg_len", "avg {n} per sentence", "平均句长 {n}", "平均句長 {n}", "平均文長 {n}"),
    ("stat.cliches", "{n} clichés", "套话 {n} 处", "套話 {n} 處", "定型表現 {n} 件"),
    ("stat.readability", "Flesch {n}", "Flesch {n}", "Flesch {n}", "Flesch {n}"),
    ("unit.word", "words", "词", "詞", "語"),
    ("unit.char", "characters", "字", "字", "文字"),
    ("unit.per100w", "per 100 words", "次/百词", "次/百詞", "100 語あたり"),
    ("unit.per100s", "per 100 sentences", "次/百句", "次/百句", "100 文あたり"),
    ("unit.cv", "coefficient of variation", "变异系数", "變異係數", "変動係数"),
    ("unit.ratio", "share", "占比", "佔比", "割合"),
    ("unit.mattr", "MATTR", "MATTR", "MATTR", "MATTR"),

    # ---------------------------------------------------------------- features
    ("feat.cliche.label", "Cliché density", "套话密度", "套話密度", "定型表現の密度"),
    ("feat.cliche.detail",
     "Weighted density of the stock phrases AI models overuse (delve into, a testament to, it is important to note…).",
     "命中 AI 常见套话（delve into、a testament to、值得注意的是…）的加权密度。",
     "命中 AI 常見套話（delve into、a testament to、值得注意的是…）的加權密度。",
     "AI が多用する定型表現（delve into、a testament to など）の加重密度。"),
    ("feat.contraction.label", "Contractions", "缩略形式", "縮略形式", "短縮形"),
    ("feat.contraction.detail",
     "How often don't / it's / we're appear. Default AI prose almost never contracts.",
     "don't / it's / we're 这类缩写的使用频率；AI 默认文本几乎不用。",
     "don't / it's / we're 這類縮寫的使用頻率；AI 預設文字幾乎不用。",
     "don't / it's / we're などの短縮形の頻度。AI の既定文ではほとんど使われません。"),
    ("feat.sent_cv.label", "Sentence-length spread", "句长变异", "句長變異", "文の長さのばらつき"),
    ("feat.sent_cv.detail",
     "How much sentence length varies. People mix long and short; AI tends toward even, medium-length sentences.",
     "句长的离散程度。人写东西长短句错落，AI 倾向于均匀的中等长度。",
     "句長的離散程度。人寫東西長短句錯落，AI 傾向於均勻的中等長度。",
     "文の長さのばらつき。人は長短を混ぜ、AI は均一な中くらいの長さに寄ります。"),
    ("feat.nominalization.label", "Nominalisation", "名词化密度", "名詞化密度", "名詞化の密度"),
    ("feat.nominalization.detail",
     "Share of abstract nouns ending in -tion / -ment / -ity — a strong sign of bureaucratic tone.",
     "-tion/-ment/-ity 等抽象名词后缀的比例，公文腔的强信号。",
     "-tion/-ment/-ity 等抽象名詞後綴的比例，公文腔的強訊號。",
     "-tion / -ment / -ity で終わる抽象名詞の割合。役所文体の強い指標。"),
    ("feat.transition.label", "Sentence openers", "句首连接词", "句首連接詞", "文頭の接続詞"),
    ("feat.transition.detail",
     "Share of sentences starting with Furthermore / Moreover / Additionally.",
     "Furthermore / Moreover / Additionally 开头的句子比例。",
     "Furthermore / Moreover / Additionally 開頭的句子比例。",
     "Furthermore / Moreover / Additionally で始まる文の割合。"),
    ("feat.short.label", "Short sentences", "短句比例", "短句比例", "短い文の割合"),
    ("feat.short.detail",
     "Share of very short sentences (≤8 words). AI expository prose almost never writes a three-word sentence; people do.",
     "极短句（≤8 词）的占比。AI 说明文几乎从不写三五个词的短句，真人会。",
     "極短句（≤8 詞）的佔比。AI 說明文幾乎從不寫三五個詞的短句，真人會。",
     "ごく短い文（8 語以下）の割合。AI の説明文はまず書きませんが、人は書きます。"),
    ("feat.trigram.label", "Trigram repetition", "三词重复率", "三詞重複率", "3 語の繰り返し"),
    ("feat.trigram.detail",
     "Repeated three-word sequences — a sign of templated phrasing.",
     "重复出现的三词组合比例，模板化表达会拉高它。",
     "重複出現的三詞組合比例，模板化表達會拉高它。",
     "3 語の並びの繰り返し。テンプレ的な表現で上がります。"),
    ("feat.mattr.label", "Lexical variety", "词汇丰富度", "詞彙豐富度", "語彙の多様性"),
    ("feat.mattr.detail", "Moving-average type-token ratio over the text.",
     "滑动窗口的类符/形符比。", "滑動視窗的類符/形符比。", "移動窓の型/延べ語比率。"),
    ("feat.hapax.label", "Rare words", "低频词比例", "低頻詞比例", "一度だけの語"),
    ("feat.hapax.detail", "Share of words used only once; lower means more formulaic.",
     "只出现一次的独特词占比，越低越套路。", "只出現一次的獨特詞佔比，越低越套路。",
     "一度しか出ない語の割合。低いほど定型的です。"),
    ("feat.word_len.label", "Average word length", "平均词长", "平均詞長", "平均語長"),
    ("feat.word_len.detail", "Longer words usually mean academic or bureaucratic register.",
     "长词比例高通常伴随学术腔/公文腔。", "長詞比例高通常伴隨學術腔/公文腔。",
     "語が長いほどアカデミック／役所文体に寄ります。"),
    ("feat.informal.label", "Informal markers", "口语化标记", "口語化標記", "口語らしい表現"),
    ("feat.informal.detail", "gonna / kinda / yeah / stuff and similar colloquialisms.",
     "gonna / kinda / yeah / stuff 这类口语词。", "gonna / kinda / yeah / stuff 這類口語詞。",
     "gonna / kinda / yeah / stuff などの口語表現。"),
    ("feat.question.label", "Questions", "疑问句比例", "疑問句比例", "疑問文の割合"),
    ("feat.question.detail", "AI expository text rarely asks questions; people often do.",
     "AI 说明文很少提问，真人写作更常自问自答。", "AI 說明文很少提問，真人寫作更常自問自答。",
     "AI の説明文はほとんど問いかけませんが、人はよく問いかけます。"),
    ("feat.opener.label", "Repeated openers", "句首重复", "句首重複", "文頭の重複"),
    ("feat.opener.detail", "Sentences that start with the same two words.",
     "多句以相同两词开头。", "多句以相同兩詞開頭。", "同じ 2 語で始まる文の多さ。"),
    ("feat.particle.label", "Sentence particles", "语气助词", "語氣助詞", "語気助詞"),
    ("feat.particle.detail", "了 / 吧 / 啊 / 呢 / 嘛 — the rough edges of spoken Chinese.",
     "了/吧/啊/呢/嘛 等语气词，正是中文口语的「毛边」所在。",
     "了/吧/啊/呢/嘛 等語氣詞，正是中文口語的「毛邊」所在。",
     "了 / 吧 / 啊 / 呢 / 嘛 など。中国語口語の「ざらつき」です。"),
    ("feat.bigram.label", "Character bigram repetition", "字二元重复", "字二元重複", "二字連鎖の繰り返し"),
    ("feat.bigram.detail", "Repeated adjacent character pairs; templated writing scores higher.",
     "相邻汉字组合的重复率，模板化表达偏高。", "相鄰漢字組合的重複率，模板化表達偏高。",
     "隣り合う 2 文字の組の繰り返し。定型文ほど高くなります。"),

    # ---------------------------------------------------------------- flags
    ("flag.high", "{label} is high", "{label}偏高", "{label}偏高", "{label}が高い"),
    ("flag.low", "{label} is low", "{label}偏低", "{label}偏低", "{label}が低い"),
    ("flag.cliche.title", "AI stock phrases found", "命中 AI 高频套话", "命中 AI 高頻套話",
     "AI の定型表現を検出"),
    ("flag.cliche.detail", "{n} hits; typical ones: {examples}.",
     "共 {n} 处，典型：{examples}。", "共 {n} 處，典型：{examples}。", "{n} 件。代表例：{examples}。"),
    ("flag.cliche.why", "Stock phrases are the easiest signal for a detector to catch.",
     "套话是最直接也最容易被检测器抓住的信号。", "套話是最直接也最容易被檢測器抓住的訊號。",
     "定型表現は検出器にとって最も分かりやすい手がかりです。"),
    ("flag.contraction.title", "Almost no contractions", "几乎没有缩略形式", "幾乎沒有縮略形式",
     "短縮形がほぼ無い"),
    ("flag.contraction.detail",
     "No don't / it's / we're anywhere. Most human writing — and speech — uses some; never using them is typical of AI output.",
     "全文没有 don't / it's / we're 这类缩写。口语与多数真人书面表达都会出现，完全不用是 AI 输出的典型特征。",
     "全文沒有 don't / it's / we're 這類縮寫。口語與多數真人書面表達都會出現，完全不用是 AI 輸出的典型特徵。",
     "don't / it's / we're が一つもありません。人の文章や会話には普通出てくるもので、"
     "皆無は AI 出力の典型的な特徴です。"),

    # ---------------------------------------------------------------- reasons
    ("reason.cliche", "clichés: {items}", "套话：{items}", "套話：{items}", "定型表現：{items}"),
    ("reason.nominal", "nominalisation {n} per 100 words", "名词化密度 {n}/百词",
     "名詞化密度 {n}/百詞", "名詞化 {n} / 100 語"),
    ("reason.no_contraction", "no contractions", "无缩略形式", "無縮略形式", "短縮形なし"),
    ("reason.transition", "opens with a discourse marker", "句首连接词开头", "句首連接詞開頭",
     "接続詞で始まる"),
    ("reason.uniform", "length matches the document average", "句长与全文均值高度一致",
     "句長與全文均值高度一致", "文長が全体平均とほぼ同じ"),

    # ---------------------------------------------------------------- humanize
    ("humanize.pane", "Source text", "原文", "原文", "元の文章"),
    ("humanize.fill", "Use the analyzer text", "取分析框文本", "取分析框文字", "分析欄の文章を使う"),
    ("humanize.placeholder",
     "Paste the text you want to make sound more natural. Rewriting only adjusts the wording — it will not add content for you.",
     "贴入想改得更自然的文字。改写只调整表达，不会替你补充内容。",
     "貼入想改得更自然的文字。改寫只調整表達，不會替你補充內容。",
     "より自然にしたい文章を貼り付けてください。表現だけを整え、内容は足しません。"),
    ("humanize.level.light", "Light", "轻微", "輕微", "軽め"),
    ("humanize.level.standard", "Standard", "标准", "標準", "標準"),
    ("humanize.level.strong", "Strong", "强力", "強力", "強め"),
    ("humanize.contractions", "Add contractions", "补英文缩写", "補英文縮寫", "短縮形を補う"),
    ("humanize.typography", "Full-width punctuation", "中文标点转全角", "中文標點轉全角",
     "句読点を全角に"),
    ("humanize.run", "Rewrite & compare", "改写并对比", "改寫並對比", "書き換えて比較"),
    ("humanize.empty",
     "Rewriting is deterministic: it strips clichés, restores verbs, adds contractions and splits long sentences. It cannot change the content.",
     "改写是确定性的规则替换：能拆套话、补缩写、打散长句，改不动的是内容本身。",
     "改寫是確定性的規則替換：能拆套話、補縮寫、打散長句，改不動的是內容本身。",
     "書き換えは決定的なルール処理です。定型表現を削り、動詞を戻し、短縮形を補い、"
     "長い文を分割します。内容そのものは変わりません。"),
    ("humanize.before", "Before", "原文", "原文", "変更前"),
    ("humanize.after", "After", "改写后", "改寫後", "変更後"),
    ("humanize.retention", "content kept {pct}", "内容保真度 {pct}", "內容保真度 {pct}",
     "内容保持率 {pct}"),
    ("humanize.strength", "strength {level}", "强度 {level}", "強度 {level}", "強度 {level}"),
    ("humanize.output", "Rewritten text", "改写结果", "改寫結果", "書き換え結果"),
    ("humanize.copy", "Copy", "复制", "複製", "コピー"),
    ("humanize.copied", "Copied", "已复制", "已複製", "コピーしました"),
    ("humanize.reanalyze", "Analyze result", "用结果再分析", "用結果再分析", "結果を分析"),
    ("change.cliche", "clichés replaced", "套话替换", "套話替換", "定型表現の置換"),
    ("change.skeleton", "skeletons flattened", "句式还原", "句式還原", "構文の単純化"),
    ("change.contraction", "contractions added", "补缩写", "補縮寫", "短縮形の補完"),
    ("change.opener", "openers trimmed", "连接词减重", "連接詞減重", "接続詞の整理"),
    ("change.split", "long sentences split", "拆长句", "拆長句", "長文の分割"),
    ("change.rhythm", "rhythm broken up", "节奏打散", "節奏打散", "リズムの分散"),
    ("change.punct", "punctuation normalised", "标点规范化", "標點規範化", "句読点の正規化"),
    ("warn.no_drop",
     "The score did not drop. That usually means the problem is structure (paragraphs too even, sentences too uniform) or the register itself — swapping words will not fix it.",
     "改写没有降低分数。通常说明问题不在用词而在结构（段落过于工整、句长过于均匀），或者这段文本的语域本身就接近 AI 默认文风。这时换词没用，得改内容组织方式。",
     "改寫沒有降低分數。通常說明問題不在用詞而在結構（段落過於工整、句長過於均勻），或者這段文字的語域本身就接近 AI 預設文風。這時換詞沒用，得改內容組織方式。",
     "スコアが下がりませんでした。多くの場合、原因は語彙ではなく構造（段落や文の長さが揃いすぎ）か、"
     "そのレジスター自体です。語を置き換えても解決しません。"),
    ("warn.retention", "Content-word retention is {pct} — the rewrite went far. Please re-read it line by line.",
     "内容词保留率 {pct}，改写幅度偏大，请逐句复核原意是否还在。",
     "內容詞保留率 {pct}，改寫幅度偏大，請逐句複核原意是否還在。",
     "内容語の保持率は {pct}。書き換えの幅が大きいので、一文ずつ確認してください。"),
    ("warn.short", "The text is short, so the score itself is noisy; do not over-read the result.",
     "原文偏短，分数本身波动很大，改写效果不宜过度解读。",
     "原文偏短，分數本身波動很大，改寫效果不宜過度解讀。",
     "文章が短いためスコアは不安定です。結果を過度に読まないでください。"),
    ("warn.responsibility",
     "Rewriting only makes the wording more natural. It does not target any specific detector and does not remove vendor watermarks; before you present the result as your own work, make sure the ideas really are yours.",
     "改写只是让文字更自然。它不针对任何具体检测器做对抗，也不移除厂商水印；把改好的稿子当成自己的作品之前，请确认内容与观点确实来自你本人。",
     "改寫只是讓文字更自然。它不針對任何具體檢測器做對抗，也不移除廠商浮水印；把改好的稿子當成自己的作品之前，請確認內容與觀點確實來自你本人。",
     "書き換えは文章を自然にするだけです。特定の検出器への対抗や、ベンダーの電子透かしの除去は行いません。"
     "自分の成果として出す前に、内容と主張が本当に自分由来か確認してください。"),

    # ---------------------------------------------------------------- marks
    ("marks.text_pane", "Text · invisible characters", "文本 · 隐形字符", "文字 · 隱形字元",
     "テキスト · 不可視文字"),
    ("marks.placeholder",
     "Paste text copied from a web page, PDF or Word to look for zero-width characters, tag characters, variation selectors and homoglyphs.",
     "粘贴从网页 / PDF / Word 复制来的文字，检查零宽字符、标签字符、变体选择符、混形字。",
     "貼上從網頁 / PDF / Word 複製來的文字，檢查零寬字元、標籤字元、變體選擇符、混形字。",
     "Web・PDF・Word からコピーした文章を貼り付け、ゼロ幅文字・タグ文字・異体字セレクタ・"
     "同形異字を確認します。"),
    ("marks.scan", "Scan invisible characters", "扫描隐形字符", "掃描隱形字元", "不可視文字を検査"),
    ("marks.clean", "Clean & copy", "清理并复制", "清理並複製", "除去してコピー"),
    ("marks.cleaned", "Cleaned {n} and copied", "已清理 {n} 个并复制", "已清理 {n} 個並複製",
     "{n} 個を除去してコピーしました"),
    ("marks.file_pane", "File · metadata / C2PA", "文件 · 元数据 / C2PA", "檔案 · 中繼資料 / C2PA",
     "ファイル · メタデータ / C2PA"),
    ("marks.drop", "Drop a file here, or", "把文件拖进来，或", "把檔案拖進來，或",
     "ファイルをここにドロップ、または"),
    ("marks.choose", "Choose file", "选择文件", "選擇檔案", "ファイルを選択"),
    ("marks.file_hint", "Read-only analysis. Decide afterwards whether to strip the metadata.",
     "只读分析；需要时再决定是否清掉元数据。", "唯讀分析；需要時再決定是否清掉中繼資料。",
     "読み取りのみ。メタデータを消すかどうかは後で決められます。"),
    ("marks.empty_title", "No character-level invisible marks found",
     "没有发现字符级隐形标记", "沒有發現字元級隱形標記", "文字レベルの不可視マークは見つかりません"),
    ("marks.empty_note",
     "{n} characters checked for zero-width characters, tag characters, variation selectors, bidi controls, unusual spaces and homoglyphs.",
     "共检查 {n} 个字符：零宽字符、标签字符、变体选择符、双向控制符、异体空格、混形字。",
     "共檢查 {n} 個字元：零寬字元、標籤字元、變體選擇符、雙向控制符、異體空格、混形字。",
     "全 {n} 文字を対象に、ゼロ幅文字・タグ文字・異体字セレクタ・双方向制御文字・特殊な空白・同形異字を確認しました。"),
    ("marks.hit", "{n} invisible characters", "命中 {n} 个隐形字符", "命中 {n} 個隱形字元",
     "不可視文字 {n} 個"),
    ("marks.chars", "{n} characters", "{n} 字符", "{n} 字元", "{n} 文字"),
    ("marks.runs", "Long runs of invisible characters", "连续隐形字符", "連續隱形字元",
     "不可視文字の連続"),
    ("marks.run_item", "{n} in a row from offset {pos}", "位置 {pos} 起连续 {n} 个",
     "位置 {pos} 起連續 {n} 個", "位置 {pos} から {n} 個連続"),
    ("marks.mixed", "Mixed-script words", "混形字", "混形字", "混在文字"),
    ("marks.mixed_item", "{script} letters mixed in", "混入{script}字母", "混入{script}字母",
     "{script}の文字が混在"),
    ("script.cyrillic", "Cyrillic", "西里尔", "西里爾", "キリル"),
    ("script.greek", "Greek", "希腊", "希臘", "ギリシャ"),

    # ---------------------------------------------------------------- invisible
    ("inv.zero_width", "Zero-width characters", "零宽字符", "零寬字元", "ゼロ幅文字"),
    ("inv.zero_width.note", "Invisible by design; often used to carry hidden data or to break up words.",
     "零宽空格/连接符本身不可见，常被用来承载隐藏信息或做分词干扰。",
     "零寬空格/連接符本身不可見，常用來承載隱藏資訊或做分詞干擾。",
     "もともと見えない文字。隠しデータの運搬や単語の分断に使われます。"),
    ("inv.tag", "Tag characters (invisible ASCII)", "标签字符（不可见 ASCII）", "標籤字元（不可見 ASCII）",
     "タグ文字（不可視 ASCII）"),
    ("inv.tag.note", "U+E0000–E007F can hide an entire ASCII paragraph where nobody can see it.",
     "U+E0000–E007F 的标签字符可以把整段 ASCII 藏进肉眼看不见的区域。",
     "U+E0000–E007F 的標籤字元可以把整段 ASCII 藏進肉眼看不見的區域。",
     "U+E0000–E007F は ASCII の段落を目に見えない場所に隠せます。"),
    ("inv.variation", "Variation selectors", "变体选择符", "變體選擇符", "異体字セレクタ"),
    ("inv.variation.note", "They control emoji presentation, but can also encode data.",
     "变体选择符用于控制 emoji 显示样式，但也能编码数据（emoji 走私）。",
     "變體選擇符用於控制 emoji 顯示樣式，但也能編碼資料（emoji 走私）。",
     "絵文字の表示を制御しますが、データを埋め込むこともできます。"),
    ("inv.bidi", "Bidirectional controls", "双向控制符", "雙向控制符", "双方向制御文字"),
    ("inv.bidi.note", "They make the rendering order differ from the byte order (Trojan Source).",
     "双向控制符会让字符显示顺序与源码顺序不一致，即 Trojan Source。",
     "雙向控制符會讓字元顯示順序與原始碼順序不一致，即 Trojan Source。",
     "表示順とバイト順が食い違います（Trojan Source）。"),
    ("inv.space", "Unusual spaces", "异体空格", "異體空格", "特殊な空白"),
    ("inv.space.note", "Non-breaking, thin and full-width spaces break layout and can hide data.",
     "异体空格（不换行空格、全角空格等）会造成排版错乱，也可能是隐写载体。",
     "異體空格（不斷行空格、全形空格等）會造成排版錯亂，也可能是隱寫載體。",
     "改行しない空白や全角空白はレイアウトを崩し、データの隠蔽にも使えます。"),
    ("inv.homoglyph", "Mixed-script homoglyphs", "跨文字系统同形字", "跨文字系統同形字", "同形異字の混在"),
    ("inv.homoglyph.note", "A Latin word containing Cyrillic or Greek letters — used for spoofing and filter bypass.",
     "同一个词里混用拉丁/西里尔/希腊字母，常用于伪装或绕过匹配。",
     "同一個詞裡混用拉丁/西里爾/希臘字母，常用於偽裝或繞過比對。",
     "ラテン語の単語にキリル／ギリシャ文字が混ざる例。偽装やフィルタ回避に使われます。"),
    ("inv.verdict.high",
     "Something worth cleaning: a hidden payload, paste residue, or a deliberate character-level mark.",
     "发现了值得处理的隐形标记：可能是隐藏载荷、复制粘贴残留或刻意的字符级标记。建议清理后再使用。",
     "發現了值得處理的隱形標記：可能是隱藏載荷、複製貼上殘留或刻意的字元級標記。建議清理後再使用。",
     "対処したほうがよい不可視文字があります。隠しデータ、コピペの残骸、意図的なマークの可能性があります。"),
    ("inv.verdict.medium", "A few invisible characters, usually paste residue from a web page or PDF. Cleaning is still worthwhile.",
     "存在少量隐形字符，多数情况是网页或 PDF 复制残留，清理掉更干净。",
     "存在少量隱形字元，多數情況是網頁或 PDF 複製殘留，清掉更乾淨。",
     "少数の不可視文字。多くは Web や PDF からのコピペ残りですが、消しておくと綺麗です。"),
    ("inv.verdict.low", "No invisible characters, but some lines end with stray spaces — usually harmless.",
     "没有发现隐形字符，但有行尾多余空格（也可能是隐写载体，一般无害）。",
     "沒有發現隱形字元，但有行尾多餘空格（也可能是隱寫載體，一般無害）。",
     "不可視文字はありませんが、行末に余分な空白があります（多くは無害）。"),
    ("inv.verdict.none",
     "No character-level hidden marks. Note: this does not rule out a statistical watermark, which only the key holder can verify.",
     "没有发现字符级隐形标记。注意：这并不排除厂商嵌入的统计水印，那类水印只能由持有密钥的一方验证。",
     "沒有發現字元級隱形標記。注意：這並不排除廠商嵌入的統計浮水印，那類浮水印只能由持有金鑰的一方驗證。",
     "文字レベルの隠しマークはありません。ただし統計的電子透かしは否定できず、検証できるのは鍵を持つ側だけです。"),

    # ---------------------------------------------------------------- metadata
    ("meta.title", "Metadata / content credentials", "元数据 / 内容凭证", "中繼資料 / 內容憑證",
     "メタデータ / コンテンツ認証"),
    ("meta.no_fields", "No readable metadata fields.", "没有发现可读的元数据字段。",
     "沒有發現可讀的中繼資料欄位。", "読み取れるメタデータはありません。"),
    ("meta.c2pa", "C2PA / JUMBF content credential found", "检测到 C2PA / JUMBF 内容凭证",
     "檢測到 C2PA / JUMBF 內容憑證", "C2PA / JUMBF コンテンツ認証を検出"),
    ("meta.ai_hints", "AI-generation traces", "AI 生成痕迹", "AI 生成痕跡", "AI 生成の痕跡"),
    ("meta.structure", "Structure", "结构", "結構", "構造"),
    ("meta.strip", "Strip metadata & download", "去掉元数据并下载", "去掉中繼資料並下載",
     "メタデータを削除してダウンロード"),
    ("meta.stripped", "Removed: {items} → {name}", "已移除：{items}，下载 {name}",
     "已移除：{items}，下載 {name}", "削除：{items} → {name}"),
    ("meta.note.png_clean", "No text chunks in this PNG; the metadata is clean.",
     "PNG 里没有任何文本块，元数据很干净。", "PNG 裡沒有任何文字區塊，中繼資料很乾淨。",
     "この PNG にテキストチャンクはありません。"),
    ("meta.note.no_meta", "This Office file has no docProps metadata.",
     "Office 文档没有 docProps 元数据。", "Office 文件沒有 docProps 中繼資料。",
     "この Office ファイルに docProps はありません。"),
    ("meta.note.pdf", "PDF metadata can live in the Info dictionary, an XMP stream and object streams. This tool reads but never rewrites PDFs — use qpdf or ExifTool.",
     "PDF 的元数据可能同时存在于 Info 字典、XMP 流和对象流中；本工具只读取不重写，清理请用 qpdf / ExifTool。",
     "PDF 的中繼資料可能同時存在於 Info 字典、XMP 流和物件流中；本工具只讀取不重寫，清理請用 qpdf / ExifTool。",
     "PDF のメタデータは Info 辞書・XMP・オブジェクトストリームに分散します。本ツールは読み取りのみで、"
     "書き換えは行いません（qpdf や ExifTool をお使いください）。"),
    ("meta.note.text", "Plain text has no binary metadata; this checks characters and embedded tool strings.",
     "纯文本文件没有二进制元数据；能查的是字符级隐形标记与内嵌的工具标识。",
     "純文字檔沒有二進位中繼資料；能查的是字元級隱形標記與內嵌的工具標識。",
     "プレーンテキストにバイナリのメタデータはありません。確認できるのは文字レベルと埋め込み文字列です。"),
    ("meta.note.c2pa",
     "C2PA is a cryptographically signed credential, verifiable with c2patool. Removing it only removes the credential — it does not change where the content came from.",
     "检测到 C2PA / JUMBF：这是密码学签名的内容凭证，可由 c2patool 验证。删掉它只会让文件失去凭证，不会改变内容来源。",
     "檢測到 C2PA / JUMBF：這是密碼學簽名的內容憑證，可由 c2patool 驗證。刪掉它只會讓檔案失去憑證，不會改變內容來源。",
     "C2PA は暗号署名された認証情報で、c2patool で検証できます。削除しても内容の出所は変わりません。"),

    # ---------------------------------------------------------------- watermark
    ("wm.title", "How statistical watermarks work", "统计水印是怎么工作的", "統計浮水印是怎麼運作的",
     "統計的電子透かしの仕組み"),
    ("wm.intro",
     "At generation time a key splits the vocabulary into a “green list”; sampling is nudged toward green tokens. "
     "To verify, the same key recomputes the list and measures how many green tokens appear. "
     "The demo below really samples two passages — one watermarked, one not — then checks each with the right key and with wrong keys.",
     "生成时用密钥把词表切成「绿名单」，只偏向绿名单里的词；验证时用同一把密钥重算，看绿名单命中率是否异常。"
     "下面这个演示会真的采样两段文本——一段加水印、一段不加——然后用正确密钥和错误密钥各检测一次。",
     "生成時用金鑰把詞表切成「綠名單」，只偏向綠名單裡的詞；驗證時用同一把金鑰重算，看綠名單命中率是否異常。"
     "下面這個演示會真的取樣兩段文字——一段加浮水印、一段不加——然後用正確金鑰和錯誤金鑰各檢測一次。",
     "生成時に鍵で語彙を「グリーンリスト」に分割し、サンプリングを緑の語に寄せます。"
     "検証では同じ鍵で再計算し、緑の語の割合が異常かを見ます。"
     "以下のデモは実際に 2 つの文章を生成し、正しい鍵と誤った鍵で検査します。"),
    ("wm.key", "Key", "密钥", "金鑰", "鍵"),
    ("wm.length", "Length", "长度", "長度", "長さ"),
    ("wm.run", "Run the demo", "跑一次演示", "跑一次演示", "デモを実行"),
    ("wm.plain", "① No watermark → checked with the right key", "① 无水印 → 用正确密钥检测",
     "① 無浮水印 → 用正確金鑰檢測", "① 透かしなし → 正しい鍵で検査"),
    ("wm.marked", "② Watermarked → checked with the right key", "② 有水印 → 用正确密钥检测",
     "② 有浮水印 → 用正確金鑰檢測", "② 透かしあり → 正しい鍵で検査"),
    ("wm.wrong", "③ Same text → {n} wrong keys", "③ 同一段水印文本 → 换 {n} 把错误密钥",
     "③ 同一段浮水印文字 → 換 {n} 把錯誤金鑰", "③ 同じ文章 → {n} 個の誤った鍵"),
    ("wm.not_detected", "all missed", "全部未检出", "全部未檢出", "すべて未検出"),
    ("wm.verdict.strong",
     "Detected: the green-list hit rate is far above chance (p < 1e-4). This text almost certainly carries a watermark for this key.",
     "显著：这段文本的绿名单命中率远超随机（p < 1e-4），几乎可以肯定带有该密钥的水印。",
     "顯著：這段文字的綠名單命中率遠超隨機（p < 1e-4），幾乎可以肯定帶有該金鑰的浮水印。",
     "検出：緑リストの命中率が偶然を大きく上回ります（p < 1e-4）。この鍵の透かしがほぼ確実にあります。"),
    ("wm.verdict.medium",
     "Suspicious: the hit rate is elevated, but the sample or the signal is not strong enough to conclude.",
     "可疑：绿名单命中率偏高，但样本量或信号强度不足以定论。",
     "可疑：綠名單命中率偏高，但樣本量或訊號強度不足以定論。",
     "疑わしい：命中率は高めですが、断定できるほどの強さではありません。"),
    ("wm.verdict.none",
     "Not detected: the hit rate matches chance, so there is no evidence of a watermark for this key.",
     "未检出：绿名单命中率与随机水平一致，没有该密钥下的水印证据。",
     "未檢出：綠名單命中率與隨機水準一致，沒有該金鑰下的浮水印證據。",
     "未検出：命中率は偶然と同水準で、この鍵の透かしの証拠はありません。"),
    ("wm.verdict.too_short",
     "Sequence too short to test — at least two tokens are needed.",
     "序列太短，无法检验（至少需要 2 个 token）。",
     "序列太短，無法檢驗（至少需要 2 個 token）。",
     "短すぎて検査できません（2 トークン以上が必要）。"),
    ("wm.green", "green {g}/{n} = {pct}", "绿名单 {g}/{n} = {pct}", "綠名單 {g}/{n} = {pct}",
     "緑 {g}/{n} = {pct}"),
    ("wm.range", "z runs {lo} to {hi}; the right key gives {z}.",
     "z 范围 {lo} ~ {hi}；真实密钥给出 z = {z}。",
     "z 範圍 {lo} ~ {hi}；真實金鑰給出 z = {z}。",
     "z は {lo} 〜 {hi}、正しい鍵では {z}。"),
    ("wm.single",
     "The green-list test is one-sided: only a surplus of green tokens counts as a detection. Wrong keys scatter around zero and occasionally reach ±2–3, which is why a single run needs a p-value and a sample size, not just a z number.",
     "绿名单检验是单侧的——只有绿 token 显著偏多才算检出。错误密钥的 z 会散布在 0 附近，偶尔到 ±2~3，所以单次检测必须看 p 值与样本量，不能只看 z 大不大。",
     "綠名單檢驗是單側的——只有綠 token 顯著偏多才算檢出。錯誤金鑰的 z 會散佈在 0 附近，偶爾到 ±2~3，所以單次檢測必須看 p 值與樣本量，不能只看 z 大不大。",
     "グリーンリスト検定は片側です。緑の語が有意に多いときだけ検出とします。誤った鍵では z が 0 付近に散らばり、"
     "ときに ±2〜3 に届くため、1 回の結果ではなく p 値とサンプル数で判断します。"),
    ("wm.note",
     "Both passages were sampled by the same toy bigram model, so the prose is nonsense — what matters is the z-score: ≈0 without a watermark, large with it, back to ≈0 under a wrong key. Real vendors (SynthID-Text and friends) use neural sampling, but the verification logic is the same: with the key you can check, without it you just see normal text.",
     "上面两段文本由同一个玩具二元语言模型采样得到，语境并不通顺——这里要看的不是文笔，而是 z 分数：未加水印时 z ≈ 0；加水印后 z 很大；换错密钥再检测又回到 0 附近。注意第三块列出的是 6 把不同错误密钥的结果：它们会散布在 0 上下，偶尔冒出一个 |z|≈2 的偶然值——这正是单次检测要报 p 值、要看样本量的原因。真实厂商的水印方案（如 SynthID-Text）用神经网络采样，但验证逻辑是同一个道理：密钥在你手上才能验，密钥不在你手上就只能看到一堆正常文本。",
     "上面兩段文字由同一個玩具二元語言模型取樣得到，語境並不順暢——這裡要看的不是文筆，而是 z 分數：未加浮水印時 z ≈ 0；加浮水印後 z 很大；換錯金鑰再檢測又回到 0 附近。注意第三塊列出的是 6 把不同錯誤金鑰的結果：它們會散佈在 0 上下，偶爾冒出一個 |z|≈2 的偶然值——這正是單次檢測要報 p 值、要看樣本量的原因。真實廠商的浮水印方案（如 SynthID-Text）用神經網路取樣，但驗證邏輯是同一個道理：金鑰在你手上才能驗，金鑰不在你手上就只能看到一堆正常文字。",
     "どちらの文章も同じおもちゃのバイグラムモデルが生成したもので、文脈は意味をなしません。"
     "見るべきは z スコアです：透かしなしで ≈0、ありで大きく、誤った鍵では再び ≈0 に戻ります。"
     "実際のベンダー（SynthID-Text など）はニューラルサンプリングを使いますが、検証の理屈は同じです。"),

    # ---------------------------------------------------------------- CLI report
    ("report.ai_likeness", "AI-likeness", "AI 相似度", "AI 相似度", "AI らしさ"),
    ("report.feature", "Feature", "特征", "特徵", "特徴"),
    ("report.value", "Value", "数值", "數值", "値"),
    ("report.weight", "Weight", "权重", "權重", "重み"),
    ("report.tendency", "Tendency", "倾向", "傾向", "傾向"),
    ("report.findings", "Findings", "诊断", "診斷", "所見"),
    ("report.sentences", "Most AI-like sentences", "最像 AI 的句子", "最像 AI 的句子", "AI らしい文"),
    ("report.rewrite", "Rewrite", "降 AI 率改写", "降 AI 率改寫", "書き換え"),
    ("report.changed", "changed", "变化", "變化", "変化"),
    ("report.retention", "content kept", "内容保真度", "內容保真度", "内容保持率"),
    ("report.invisible", "Invisible-character scan", "隐形字符扫描", "隱形字元掃描", "不可視文字の検査"),
    ("report.meta", "Metadata / content credentials", "元数据 / 内容凭证", "中繼資料 / 內容憑證",
     "メタデータ / コンテンツ認証"),
    ("report.watermark", "Statistical watermark demo (green-list)", "统计水印演示（绿名单方案）",
     "統計浮水印演示（綠名單方案）", "統計的電子透かしのデモ（グリーンリスト）"),
    ("report.confidence", "confidence {level}", "可信度 {level}", "可信度 {level}", "信頼度 {level}"),
    ("report.no_content", "Input is empty.", "输入是空的。", "輸入是空的。", "入力が空です。"),
]

CATALOG: dict[str, dict[str, str]] = {
    key: {"en": en, "zh-CN": zh_cn, "zh-TW": zh_tw, "ja": ja}
    for key, en, zh_cn, zh_tw, ja in _ROWS
}


def t(key: str, locale: str | None = None, **kwargs) -> str:
    """Translate *key* into *locale*, formatting ``{placeholders}`` when given."""
    loc = resolve(locale)
    entry = CATALOG.get(key)
    if entry is None:
        return key
    text = entry.get(loc) or entry.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def band_label(band_key: str, locale: str | None = None) -> str:
    return t(f"result.band.{band_key}", locale)


def confidence_label(confidence: str, locale: str | None = None) -> str:
    mapping = {"较高": "high", "中等": "medium", "较低": "low", "很低": "very_low"}
    return t(f"result.conf.{mapping.get(confidence, 'medium')}", locale)


def strings(locale: str | None = None) -> dict[str, str]:
    """All strings for one locale — used by the web UI."""
    loc = resolve(locale)
    return {k: (v.get(loc) or v.get("en") or k) for k, v in CATALOG.items()}


def missing() -> dict[str, list[str]]:
    """Keys missing a translation, per locale (used by the test-suite)."""
    out: dict[str, list[str]] = {loc: [] for loc in LOCALES}
    for key, entry in CATALOG.items():
        for loc in LOCALES:
            if not entry.get(loc):
                out[loc].append(key)
    return out
