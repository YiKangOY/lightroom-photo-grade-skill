#!/usr/bin/env python3
"""Build a searchable, provenance-preserving style index for Nikon recipes.

Official descriptions remain verbatim in the index. Everything under ``analysis``
is an explicitly labelled workflow inference from the public description and the
single official display sample; it is not an official Nikon characterization.
"""

from __future__ import annotations

import argparse
import colorsys
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageStat


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "references" / "nikon-cloud" / "catalog-source.json"
INDEX = ROOT / "references" / "nikon-cloud" / "style-index.json"
CATALOG_MD = ROOT / "references" / "nikon-cloud" / "catalog.md"


RED_OVERRIDES = {
    "01KBXVV95S83XYQC61W1Z5XHFB": {
        "summary_zh": "干净、克制的冷调电影基底：蓝绿环境被轻度强化，肤色自然但微冷，深阴影平滑而不硬，适合作为现代叙事的通用起点。",
        "palette": ["冷青蓝", "克制绿色", "自然微冷肤色"],
        "tone": "中等反差；暗部深但过渡顺滑，高光不追求耀眼",
        "mood_tags": ["电影感", "现代", "内敛", "叙事"],
        "scene_tags": ["人像", "城市", "室内", "生活方式"],
        "best_for": "画面已有蓝绿环境色、希望兼顾肤色与冷调电影感的现代叙事。",
        "avoid_when": "夕阳暖色是主体，或需要明亮甜美、强烈金黄色氛围时。",
        "lightroom_semantic_moves": ["白平衡轻微偏冷，先保护肤色", "蓝/青/绿适度聚拢，避免荧光化", "压稳高光并建立深而柔的阴影", "整体饱和度克制，橙色肤色单独保真"],
    },
    "01KBXVV9F5TRD8DA11S2W9JWPW": {
        "summary_zh": "柔和青绿雾感的冷调电影风：蓝色向青移动，绿色更浓，肤色偏冷且低饱和，整体安静、内省。",
        "palette": ["雾青", "冷绿", "低饱和肤色"],
        "tone": "中低反差；阴影柔和，高光收敛，层次偏空气感",
        "mood_tags": ["电影感", "静谧", "忧郁", "内省"],
        "scene_tags": ["室内", "窗光人像", "阴天", "安静叙事"],
        "best_for": "柔和室内光、阴天或本身偏冷且不靠强烈色彩取胜的画面。",
        "avoid_when": "需要健康暖肤、阳光灿烂或高反差硬朗质感时。",
        "lightroom_semantic_moves": ["色温偏冷并轻推青绿关系", "降低橙黄饱和但保留皮肤明度", "压低整体反差，保持阴影分离", "让蓝色向青靠拢但避免污染中性色"],
    },
    "01KBXVV9RMJBPDCZ1JM8Q57MZP": {
        "summary_zh": "清脆青蓝与强结构反差：冷色占主导，阴影深、边界明确，色彩浓郁但不过饱和，强调人物与空间层次。",
        "palette": ["清脆青蓝", "深冷阴影", "自然冷肤色"],
        "tone": "高反差；暗部扎实，高光与阴影细节仍需保留",
        "mood_tags": ["电影感", "锐利", "前卫", "力量"],
        "scene_tags": ["环境人像", "城市", "建筑", "硬光"],
        "best_for": "有明确光影结构、线条或层次，需要冷峻冲击力的环境人像与城市画面。",
        "avoid_when": "柔美低反差人像、雾气场景或肤色已经偏青时。",
        "lightroom_semantic_moves": ["以曲线建立强而可控的明暗结构", "蓝青适度加深并统一", "压住综合色度，保留橙色肤色分离", "高光与黑位避免同时剪切"],
    },
    "01KBXVVA9H533XHSSBQ1RH6A54": {
        "summary_zh": "青色笼罩的冷峻黑色电影感：蓝绿突出、暖色退场，冷肤色融入环境，深黑阴影制造神秘与反乌托邦气质。",
        "palette": ["主导青色", "冷蓝绿", "被抑制红橙"],
        "tone": "深暗高反差；黑位浓重，中间调压低",
        "mood_tags": ["黑色电影", "神秘", "反乌托邦", "冷峻"],
        "scene_tags": ["夜景", "工业空间", "戏剧人像", "概念摄影"],
        "best_for": "暗调、工业或夜间叙事，且允许肤色融入整体冷色世界的画面。",
        "avoid_when": "肤色准确性优先、家庭纪实、婚礼或暖色商品摄影。",
        "lightroom_semantic_moves": ["显著建立青色环境主导关系", "降低红橙存在感但不可造成病态断层", "压深黑位并保留关键阴影纹理", "控制蓝绿高饱和区域，避免色块化"],
    },
    "01KBXVVASPV32SKAKKFQ08MR5Y": {
        "summary_zh": "粗粝与辉光并存的高反差风格：冷阴影托起鲜亮橙红，高光明亮、暗部有重量，画面充满速度与张力。",
        "palette": ["冷阴影", "高能橙红", "冷暖肤色"],
        "tone": "高反差；深阴影与明亮高光并置，强调视觉张力",
        "mood_tags": ["电影感", "粗粝", "动感", "强烈"],
        "scene_tags": ["动作", "音乐现场", "时尚", "城市夜景"],
        "best_for": "本身有红橙光源或暖色主体、需要从冷背景中跳出的动态叙事。",
        "avoid_when": "光比已经失控、皮肤过红，或需要柔和低调的日常记录时。",
        "lightroom_semantic_moves": ["先恢复高光和阴影可用细节，再做强反差", "强化橙红与冷阴影的分离", "肤色在冷暖之间保持连续过渡", "限制红色饱和峰值，避免溢色"],
    },
    "01KBXVVB156N1AE0ZF7R983D15": {
        "summary_zh": "实验性的绿色侵入：冷绿覆盖中间调，蓝绿形成超现实冲击，深阴影强化戏剧性，肤色也主动偏冷。",
        "palette": ["强冷绿", "实验蓝", "冷化肤色"],
        "tone": "中高反差；阴影深，中间调色偏强烈",
        "mood_tags": ["实验", "超现实", "前卫", "异质"],
        "scene_tags": ["概念人像", "时尚", "舞台", "创意影像"],
        "best_for": "允许明显偏色、追求非自然世界观的概念、时尚或音乐视觉。",
        "avoid_when": "纪实、婚礼、产品颜色准确或自然肤色必须优先时。",
        "lightroom_semantic_moves": ["将绿偏置集中在阴影与环境色，避免全域平涂", "蓝绿做明确色相分工", "肤色只保留最低限度可读性", "用黑位与中间调反差支撑实验色"],
    },
    "01KBXVVB5MCPQSTAM83NKMDPTG": {
        "summary_zh": "比标准 CineBias 更温和含蓄的冷调电影风：柔蓝绿环境包围略暖、低饱和的自然肤色，阴影轻柔，叙事感不抢内容。",
        "palette": ["柔蓝绿", "低饱和暖肤", "中性冷灰"],
        "tone": "低至中等反差；阴影柔软，层次细腻",
        "mood_tags": ["电影感", "含蓄", "宁静", "自然"],
        "scene_tags": ["剧情人像", "生活方式", "旅行", "室内"],
        "best_for": "希望获得电影色彩关系，但不想让调色压过人物与故事的画面。",
        "avoid_when": "需要强烈商业鲜艳度、硬朗黑位或高能量视觉时。",
        "lightroom_semantic_moves": ["轻微冷却环境，中间调保留一点暖肤", "降低综合色度而保持色相分离", "用柔和曲线而非硬对比塑形", "避免把阴影压成纯黑"],
    },
    "01KBXVVBBYAZ7829PGCZ9J3T92": {
        "summary_zh": "强调纹理与光影叙事的黑白电影风：黑色深、灰阶柔、高光明亮，反差强但过渡不生硬。",
        "palette": ["中性黑白", "深黑", "明亮高光"],
        "tone": "高反差黑白；中间灰平滑，兼顾面部和纹理",
        "mood_tags": ["黑白", "真实", "永恒", "情绪"],
        "scene_tags": ["人像", "纪实", "街头", "光影"],
        "best_for": "形体、表情、纹理和光线比颜色更重要的真实叙事。",
        "avoid_when": "颜色承担主题信息，或平光素材缺少足够明暗结构时。",
        "lightroom_semantic_moves": ["先用综合色彩明度关系塑造黑白分离", "建立深黑与亮高光但保留端点", "让肤色对应灰阶自然明亮", "不依赖清晰度或纹理增强制造锐感"],
    },
    "01KBXVVBGN0D5X8S4VKDFPKSQE": {
        "summary_zh": "经典漂白跳过观感：高反差、低饱和、偏冷金属质感，苍白肤色与浓烈阴影带来严肃、粗粝、前卫的戏剧张力。",
        "palette": ["冷金属灰", "低饱和肤色", "残留冷色"],
        "tone": "很高反差；亮部偏硬，阴影浓重，综合色彩收缩",
        "mood_tags": ["漂白跳过", "粗粝", "严肃", "前卫"],
        "scene_tags": ["时尚", "动作", "工业", "暗黑叙事"],
        "best_for": "硬光、材质明显、主题严肃的时尚或电影画面。",
        "avoid_when": "柔美人像、婴童、食物，或素材高光/阴影已经严重剪切时。",
        "lightroom_semantic_moves": ["大幅降低综合色度但保留少量冷色辨识", "以曲线建立强反差并守住端点细节", "肤色变淡而非简单变灰", "利用白平衡与HSL形成冷金属倾向"],
    },
}


TAG_RULES = {
    "scene_tags": {
        "人像": r"人像|肖像|肤色|人物|模特|portrait",
        "风景": r"风景|自然风光|景观|landscape",
        "街头": r"街头|街拍|扫街|快照|城市|street",
        "夜景": r"夜景|夜间|低光|霓虹|蓝调时刻|灯光|night",
        "室内": r"室内|咖啡馆|影棚|棚拍|家人|晚餐",
        "自然": r"森林|树林|植物|花卉|绿植|水体|天空|海|荒野|动物|猫咪|自然",
        "旅行": r"旅行|旅拍|汽车|火车|飞机",
        "建筑": r"建筑|工业|城市风光",
        "静物": r"静物|桌面|美食|商品",
        "视频": r"视频|片段|10位|电影项目",
    },
    "mood_tags": {
        "电影感": r"电影|cinematic|filmic|movie|cine",
        "复古": r"复古|怀旧|胶片|film|过期胶卷|永恒",
        "柔和": r"柔和|柔美|细腻|温柔|朦胧|空灵|梦幻|粉彩",
        "清新": r"清新|通透|透明感|清爽|明快|澄澈",
        "忧郁": r"忧郁|沉稳|神秘|阴郁|moody",
        "温暖": r"温暖|温馨|暖意|金色|琥珀|夕阳|日落",
        "强烈": r"强烈|鲜明|冲击|张力|前卫|大胆|戏剧",
        "宁静": r"宁静|平静|舒缓|内省|静谧",
        "自然": r"自然感|自然且|真实|通用性|日常",
        "鲜艳": r"鲜艳|生动|活力|浓郁|饱和度.*提升|高饱和",
        "黑白": r"黒白|黑白|灰度|achrom",
    },
}


PALETTE_RULES = [
    ("黑白灰阶", r"黒白|黑白|灰度|achrom"),
    ("青蓝", r"青色|青蓝|蓝色.*青|teal|cyan|turquoise"),
    ("冷蓝", r"冷色|冷调|蓝色|blue"),
    ("绿色", r"绿色|绿意|森林绿|green"),
    ("暖橙", r"橙色|橙黄|orange"),
    ("金黄", r"金色|黄色|琥珀|gold|sunset"),
    ("红色", r"红色|red"),
    ("粉色/洋红", r"粉色|粉红|洋红|magenta|pink|rose"),
    ("棕褐/大地色", r"棕|褐|大地色|brown"),
    ("柔和中性色", r"米色|白色|中性色|淡雅|自然色"),
]


def clean_text(value: str) -> str:
    value = (value or "").replace("创作者的说明", "").strip()
    return re.sub(r"\s+", " ", value)


def image_metrics(path: Path) -> dict:
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        rgb.thumbnail((256, 256))
        pixels = list(rgb.getdata())
    lum = sorted((0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 for r, g, b in pixels)
    sats, hues = [], []
    for r, g, b in pixels:
        h, s, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        sats.append(s)
        if s > 0.08:
            hues.append(h * 360)
    sats.sort()
    stat = ImageStat.Stat(rgb)
    def q(values, pct):
        return values[min(len(values) - 1, max(0, int((len(values) - 1) * pct)))]
    mean_l = sum(lum) / len(lum)
    variance = sum((x - mean_l) ** 2 for x in lum) / len(lum)
    return {
        "sample_only": True,
        "width": im.width,
        "height": im.height,
        "luminance_mean": round(mean_l, 3),
        "luminance_std": round(math.sqrt(variance), 3),
        "luminance_p10": round(q(lum, .10), 3),
        "luminance_p90": round(q(lum, .90), 3),
        "saturation_mean": round(sum(sats) / len(sats), 3),
        "saturation_p90": round(q(sats, .90), 3),
        "mean_rgb": [round(x / 255, 3) for x in stat.mean],
        "dominant_hue_mean_degrees": round(sum(hues) / len(hues), 1) if hues else None,
    }


def find_tags(text: str, group: str) -> list[str]:
    return [label for label, pattern in TAG_RULES[group].items() if re.search(pattern, text, re.I)]


def palette(text: str, metrics: dict) -> list[str]:
    result = [label for label, pattern in PALETTE_RULES if re.search(pattern, text, re.I)]
    if not result:
        r, g, b = metrics["mean_rgb"]
        if b > r + .025:
            result.append("样张偏冷")
        elif r > b + .035:
            result.append("样张偏暖")
        else:
            result.append("样张中性")
    return result[:4]


def tone_text(text: str, metrics: dict, control: dict) -> str:
    if re.search(r"高对比|强烈.*对比|反差感强|对比度.*加强|高反差", text, re.I):
        contrast = "偏高反差"
    elif re.search(r"低对比|降低对比|对比度.*低|柔化.*亮部.*暗部", text, re.I):
        contrast = "偏低反差"
    else:
        c = str(control.get("contrast", ""))
        try:
            n = float(c)
            contrast = "偏高反差" if n >= 20 else "偏低反差" if n <= -20 else "中等反差"
        except ValueError:
            contrast = "中等反差"
    if re.search(r"阴影.*深|深邃.*阴影|暗部.*更暗|黑位", text, re.I):
        shadow = "深阴影"
    elif re.search(r"提亮.*阴影|柔化阴影|暗部细节|保护.*阴影", text, re.I):
        shadow = "开放阴影"
    else:
        shadow = "阴影自然"
    if re.search(r"柔化.*亮部|降低亮部|高光.*柔", text, re.I):
        highlight = "柔和高光"
    elif re.search(r"明亮.*高光|提升亮部|亮部.*鲜艳", text, re.I):
        highlight = "明亮高光"
    else:
        highlight = "高光适中"
    return f"{contrast}；{shadow}，{highlight}（结合官方文字与单张展示样张判断）"


def saturation_label(text: str, metrics: dict, control: dict) -> str:
    if re.search(r"低饱和|降低.*饱和|减弱.*色|褪色|色度.*抑制|不饱和", text, re.I):
        return "克制/低饱和"
    if re.search(r"高饱和|饱和度.*提升|饱和度.*加强|鲜艳|浓郁|生动", text, re.I):
        return "鲜明/较高饱和"
    s = str(control.get("saturation", ""))
    try:
        n = float(s)
        return "鲜明/较高饱和" if n >= 15 else "克制/低饱和" if n <= -15 else "中等饱和"
    except ValueError:
        return "中等饱和" if metrics["saturation_mean"] < .45 else "鲜明/较高饱和"


def make_summary(name: str, palettes: list[str], tone: str, sat: str, moods: list[str], official: str) -> str:
    character = "、".join(moods[:3]) or "自然"
    lead = re.split(r"[。！？]", official)[0].strip()
    if len(lead) > 64:
        lead = lead[:64] + "…"
    return f"{name}：以{'、'.join(palettes)}为主要关系，{tone.split('（')[0].rstrip()}，综合色彩呈{sat}；整体偏{character}。官方描述核心：{lead}。"


def semantic_moves(palettes: list[str], tone: str, sat: str, scenes: list[str]) -> list[str]:
    moves = ["先校正目标照片的基础曝光与中性色，再建立风格关系"]
    joined = " ".join(palettes)
    if "黑白" in joined:
        moves.append("用各色明度关系建立灰阶分离，保留肤色与主体可读性")
    elif any(x in joined for x in ("青", "蓝", "绿", "冷")):
        moves.append("先用白平衡确定冷暖基线，再以HSL整理蓝、青、绿的相对关系")
    if any(x in joined for x in ("橙", "黄", "红", "粉", "棕", "暖")):
        moves.append("保护橙红肤色或暖色主体，避免综合色偏色覆盖局部关系")
    if "偏高反差" in tone:
        moves.append("以色调曲线建立反差，同时守住高光与黑位细节")
    elif "偏低反差" in tone:
        moves.append("柔化亮暗端点，保持中间调层次而非简单提灰")
    else:
        moves.append("用温和曲线维持中等反差和自然层次")
    moves.append("降低综合色度" if "低饱和" in sat else "按主体分区控制饱和度，避免全局过艳")
    if "人像" in scenes:
        moves.append("最后复核肤色连续性与面部明度，不让风格色污染皮肤")
    return moves[:5]


def infer(entry: dict, metrics: dict) -> dict:
    official = clean_text(entry.get("official_description", ""))
    combined = f"{entry.get('name','')} {official}"
    scenes = find_tags(combined, "scene_tags") or ["通用/待按样张复核"]
    moods = find_tags(combined, "mood_tags") or ["自然"]
    colors = palette(combined, metrics)
    tone = tone_text(combined, metrics, entry.get("picture_control", {}))
    sat = saturation_label(combined, metrics, entry.get("picture_control", {}))
    best = f"优先用于{ '、'.join(scenes[:4]) }，尤其当原片已经具备与样张相近的光线和主体色关系时。"
    avoid = "若原片主色、光质或肤色条件与展示样张相反，应降低匹配权重并改选其他配方。"
    return {
        "provenance": "workflow_inference_from_official_text_and_one_display_sample",
        "summary_zh": make_summary(entry["name"], colors, tone, sat, moods, official),
        "palette": colors,
        "tone": tone,
        "saturation": sat,
        "mood_tags": moods,
        "scene_tags": scenes,
        "best_for": best,
        "avoid_when": avoid,
        "lightroom_semantic_moves": semantic_moves(colors, tone, sat, scenes),
        "confidence": "medium",
        "caveat": "仅依据创作者公开说明与一张官方展示样张；应用前必须查看样张并结合目标原片重新判断。",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=INDEX)
    parser.add_argument("--markdown", type=Path, default=CATALOG_MD)
    args = parser.parse_args()
    source = json.loads(args.catalog.read_text(encoding="utf-8"))
    records = []
    for entry in source["entries"]:
        sample = (args.catalog.parent / entry["sample"]["local_path"]).resolve()
        metrics = image_metrics(sample)
        analysis = infer(entry, metrics)
        if entry["id"] in RED_OVERRIDES:
            analysis.update(RED_OVERRIDES[entry["id"]])
            analysis["saturation"] = saturation_label(clean_text(entry["official_description"]), metrics, entry.get("picture_control", {}))
            analysis["confidence"] = "high_manual_review"
            analysis["provenance"] = "manually_curated_workflow_inference_from_official_text_and_display_sample"
        records.append({
            "id": entry["id"], "name": entry["name"], "photographer": entry["photographer"],
            "public_date": entry.get("public_date"), "source_page": entry["source_page"],
            "sample_path": entry["sample"]["local_path"], "sample_sha256": entry["sample"]["sha256"],
            "official_description": clean_text(entry.get("official_description", "")),
            "picture_control_name": entry.get("picture_control_name"),
            "picture_control_reference": entry.get("picture_control", {}),
            "camera": entry.get("camera"), "lens": entry.get("lens"),
            "image_stats": metrics, "analysis": analysis,
        })
    output = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_catalog": args.catalog.name,
        "source_url": source["source"],
        "record_count": len(records),
        "interpretation_notice": "official_description and picture_control_reference are source data; analysis is a non-official workflow inference. Sample statistics describe only the single display image.",
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    grouped = defaultdict(list)
    for item in records:
        grouped[item["photographer"]].append(item)
    lines = ["# Nikon Imaging Cloud 配方目录", "", f"共 {len(records)} 个公开配方、{len(grouped)} 位署名创作者。官方说明与工作流解读严格分开；样张仅供本地风格匹配。", ""]
    for photographer in sorted(grouped, key=str.casefold):
        lines += [f"## {photographer}", ""]
        for item in grouped[photographer]:
            a = item["analysis"]
            lines.append(f"- **{item['name']}** (`{item['id']}`) — {a['summary_zh']} [公开来源]({item['source_page']})")
        lines.append("")
    args.markdown.write_text("\n".join(lines), encoding="utf-8")
    print(f"Built {len(records)} records for {len(grouped)} photographers")


if __name__ == "__main__":
    main()
