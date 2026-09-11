#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Danbooru 标签数据集生成 ComfyUI_TagSelect 需要的两个数据文件。

输入（放在仓库的 .work/ 目录下，可用参数覆盖）:
    supermarket.json  317,423 行，每行 [英文标签, 中文名, danbooru分类, 投稿量]
                      分类：0=通用 1=画师 3=作品 4=角色 5=元标签
    danbooru.csv      a1111 tagcomplete 的别名表： tag,category,count,"alias1,alias2"

输出:
    assets/data/tags_core.json    精选可浏览标签（按语义分类，启动时同步加载）
    assets/data/tags_full.tsv.gz  全量标签（后台加载，用于全库搜索）

用法:
    python tools/build_data.py [--input-dir .work] [--output-dir assets/data]
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


from _utf8 import force_utf8

force_utf8()

ROOT = Path(__file__).resolve().parent.parent

# danbooru 原始分类
D_GENERAL, D_ARTIST, D_COPYRIGHT, D_CHARACTER, D_META = 0, 1, 3, 4, 5

# ---------------------------------------------------------------------------
# 分类定义（顺序即优先级顺序）
# ---------------------------------------------------------------------------
CATEGORY_ORDER = [
    ("quality", "画质与负面"),
    ("meta", "元标签"),
    ("people", "人数构图"),
    ("hair", "头发"),
    ("eyes", "眼睛"),
    ("face", "表情"),
    ("body", "身体"),
    ("clothing", "服装"),
    ("uniform", "制服职业"),
    ("accessory", "配饰"),
    ("pose", "姿势动作"),
    ("scene", "场景背景"),
    ("nature", "自然天气"),
    ("camera", "视角镜头"),
    ("lighting", "光影色彩"),
    ("style", "画风风格"),
    ("object", "物品道具"),
    ("creature", "动物生物"),
    ("theme", "题材世界观"),
    ("character", "角色"),
    ("series", "作品系列"),
    ("artist", "画师"),
    ("r18", "R18"),
]

# 每个分类进入"核心库"的标签数量上限
CORE_CAPS = {
    "quality": 400, "meta": 300, "people": 300, "hair": 900, "eyes": 400,
    "face": 900, "body": 1200, "clothing": 2200, "uniform": 900, "accessory": 900,
    "pose": 1600, "scene": 1400, "nature": 900, "camera": 700, "lighting": 700,
    "style": 800, "object": 1200, "creature": 400, "theme": 700,
    "character": 3000, "series": 1200, "artist": 400, "r18": 2500,
}

# ---------------------------------------------------------------------------
# 手工补充的「提示词词条」。
# masterpiece / best_quality / bad_hands 这类词并不是 Danbooru 标签，
# 但它们是 NovelAI / SD 生态里最常用的画质与负面提示词，必须能选到。
# ---------------------------------------------------------------------------
EXTRA_PROMPT_TAGS: dict[str, list[tuple[str, str]]] = {
    "quality": [
        # 正向画质
        ("masterpiece", "杰作"),
        ("best_quality", "最佳质量"),
        ("amazing_quality", "极佳质量"),
        ("very_aesthetic", "极具美感"),
        ("aesthetic", "美感"),
        ("good_quality", "良好质量"),
        ("normal_quality", "普通质量"),
        ("high_quality", "高质量"),
        ("ultra_detailed", "超精细"),
        ("extremely_detailed", "极其精细"),
        ("intricate_details", "复杂细节"),
        ("high_detail", "高细节"),
        ("best_shading", "最佳光影"),
        ("official_art", "官方画风"),
        ("extremely_detailed_cg_unity_8k_wallpaper", "极致精细 CG"),
        ("very_aesthetic_lighting", "极具美感的光影"),
        ("beautiful", "美丽"),
        ("stunning", "惊艳"),
        ("detailed", "细节丰富"),
        # 通用负面 / 崩坏修复
        ("worst_quality", "最差质量"),
        ("low_quality", "低质量"),
        ("bad_anatomy", "人体崩坏"),
        ("bad_hands", "手部崩坏"),
        ("bad_proportions", "比例失调"),
        ("bad_perspective", "透视错误"),
        ("poorly_drawn", "画工粗糙"),
        ("mutated_hands", "畸形的手"),
        ("mutated", "畸形"),
        ("deformed", "变形"),
        ("disfigured", "五官错乱"),
        ("malformed_limbs", "肢体畸形"),
        ("missing_limb", "缺少肢体"),
        ("extra_digits", "多余的手指"),
        ("fewer_digits", "手指过少"),
        ("missing_fingers", "缺失手指"),
        ("fused_fingers", "手指粘连"),
        ("extra_limbs", "多余肢体"),
        ("extra_arms", "多余手臂"),
        ("extra_legs", "多余的腿"),
        ("long_neck", "长脖子"),
        ("ugly", "丑陋"),
        ("worst_quality_art", "劣质画作"),
        # 文字 / 水印
        ("watermark", "水印"),
        ("signature", "签名"),
        ("username", "用户名"),
        ("artist_name", "画师名"),
        ("web_address", "网址"),
        ("text", "文字"),
        ("english_text", "英文文字"),
        ("logo", "标志"),
        ("speech_bubble", "对话框"),
        ("censored", "打码"),
        ("mosaic_censoring", "马赛克打码"),
        ("bar_censor", "条状打码"),
        ("jpeg_artifacts", "JPEG 压缩伪影"),
        ("blurry", "模糊"),
        ("lowres", "低分辨率"),
        ("sketch", "草图"),
        ("unfinished", "未完成"),
        ("simple_background", "简单背景"),
        ("solid_background", "纯色背景"),
        ("white_background", "白色背景"),
        ("black_background", "黑色背景"),
        ("transparent_background", "透明背景"),
        ("gradient_background", "渐变背景"),
        ("out_of_frame", "出画"),
        ("cropped", "被裁切"),
    ],
}

# ---------------------------------------------------------------------------
# 画质词白名单（优先级最高，避免被别的规则抢走）
# ---------------------------------------------------------------------------
QUALITY_EXACT = {
    # 正向
    "masterpiece", "best_quality", "amazing_quality", "very_aesthetic", "aesthetic",
    "good_quality", "normal_quality", "high_quality", "ultra_detailed", "extremely_detailed",
    "intricate_details", "high_detail", "highres", "absurdres", "high_resolution",
    "official_art", "best_shading", "detailed_shading", "beautiful", "stunning",
    "newest", "recent", "year_2025", "year_2024", "year_2023", "year_2022", "year_2021",
    "year_2020", "year_2019", "year_2018", "mid_2010s", "early_2010s", "late_2010s",
    # 负向 / 崩坏修复 / 画面卫生
    "worst_quality", "low_quality", "lowres", "bad_anatomy", "bad_hands",
    "bad_proportions", "bad_perspective", "extra_digits", "fewer_digits",
    "extra_limbs", "missing_limbs", "extra_arms", "extra_legs", "extra_ears",
    "extra_eyes", "extra_fingers", "missing_fingers", "fused_fingers",
    "long_neck", "blurry", "jpeg_artifacts", "pixelated", "unfinished",
    "out_of_frame", "cropped", "simple_background", "solid_background",
    "white_background", "black_background", "transparent_background",
    "gradient_background", "text", "signature", "watermark", "username",
    "artist_name", "web_address", "logo", "copyright_name", "english_text",
    "speech_bubble", "thought_bubble", "mosaic_censoring", "bar_censor",
    "censored", "convenient_censoring",
}
# ---------------------------------------------------------------------------
# R18：先做整词匹配，再用排除表挡住误伤
# ---------------------------------------------------------------------------
R18_EXACT = {
    # 裸露
    "nude", "naked", "topless", "bottomless", "completely_nude", "partially_nude",
    "almost_nude", "nude_filter", "undressing", "no_bra", "no_panties", "nipples",
    "nipple_slip", "erect_nipples", "puffy_nipples", "inverted_nipples",
    "covered_nipples", "areola", "large_areolae", "puffy_areolae", "pubic_hair",
    "crotch", "groin", "exposed_breast", "breast_slip", "wardrobe_malfunction",
    # 性器官
    "penis", "pussy", "vagina", "clitoris", "testicles", "anus", "anal",
    "urethra", "glans", "foreskin", "labia", "vulva", "bulge", "cameltoe",
    # 性行为
    "sex", "vaginal", "oral", "fellatio", "cunnilingus", "masturbation", "handjob",
    "paizuri", "titjob", "cum", "cumshot", "semen", "ejaculation", "orgasm",
    "ahegao", "after_sex", "impending_sex", "sex_from_behind", "missionary",
    "doggystyle", "cowgirl_position", "mating_press", "suspended_congress",
    "fingering", "deepthroat", "irrumatio", "bukkake", "creampie", "excessive_cum",
    "gangbang", "threesome", "group_sex", "orgy", "rape", "netorare", "futanari",
    "futa", "hentai", "nsfw", "explicit", "rating_explicit", "rating_questionable",
    "uncensored", "sex_toy", "dildo", "vibrator", "onahole", "anal_beads",
    "butt_plug", "sex_machine", "used_condom", "condom", "pantyshot", "upskirt",
    "underboob", "sideboob", "downblouse", "voyeurism", "exhibitionism",
    "bondage", "bdsm", "shibari", "bound_wrists", "bound_ankles", "rope_bondage",
    "tentacle_rape", "bestiality", "incest", "loli", "shota", "lolicon", "shotacon",
    "pubic", "prostate", "squirting", "female_ejaculation", "peeing", "urination",
}
# 命中 R18 词元但应该放行的标签
R18_GUARD = {
    "bondage_pants", "bondage_fairy", "analog", "analysis", "analytics",
    "analogue", "canal", "sextet", "grape", "grapefruit", "grapejuice",
    "therapist", "cucumber", "document", "accumulate", "circumstance",
    "lolita_fashion", "lolita_hair", "peninsula", "uranus", "manus",
    "nipple_piercing",
}
R18_TOKENS = {
    "nude", "naked", "nipples", "areola", "areolae", "penis", "pussy", "vagina",
    "clitoris", "testicles", "anus", "semen", "cumshot", "cum", "bukkake",
    "creampie", "fellatio", "cunnilingus", "masturbation", "handjob", "paizuri",
    "futanari", "hentai", "nsfw", "rape", "netorare", "bestiality", "shibari",
    "bdsm", "bondage", "ahegao", "dildo", "vibrator", "onahole", "orgasm",
    "uncensored", "lolicon", "shotacon", "exhibitionism", "voyeurism",
    # "sex" 用整词匹配是安全的：sextuplets / sexual_harassment / sexually_suggestive
    # 都只是一个词元的一部分，不会被误伤
    "sex", "penetration", "insertion", "orgy", "threesome", "foursome",
    "gangbang", "lactation", "undressing", "stripping", "striptease",
    "deepthroat", "irrumatio", "squirting", "urination", "peeing",
    "molestation", "prostitute", "prostitution", "brothel", "censored_nipples",
    "condom", "pillow_hug", "humping", "grinding", "clothed_sex",
    "pubic", "genital", "genitalia", "erection", "ecchi", "lewd",
}

# ---------------------------------------------------------------------------
# 各分类的关键词规则
# ---------------------------------------------------------------------------
HAIR_EXACT = {
    "twintails", "ahoge", "ponytail", "braid", "braids", "sidelocks", "hime_cut",
    "bob_cut", "pixie_cut", "undercut", "mohawk", "bowl_cut", "curly_hair",
    "dreadlocks", "hair_bun", "double_bun", "cone_hair", "drill_hair", "bangs",
    "swept_bangs", "blunt_bangs", "hair_between_eyes", "hair_intakes", "widow_s_peak",
    "antenna_hair", "wavy_hair", "straight_hair", "messy_hair", "floating_hair",
    "wet_hair", "shiny_hair", "multicolored_hair", "two_tone_hair", "gradient_hair",
    "streaked_hair", "colored_inner_hair", "single_hair_strand", "hair_strand",
    "hair_over_one_eye", "hair_over_eyes", "hair_pulled_back", "hair_up",
    "hair_down", "short_hair", "medium_hair", "long_hair", "very_long_hair",
    "absurdly_long_hair", "big_hair", "hair_spread_out", "hair_flip",
    "hair_covering_breast", "hair_covering_face", "hair_covering_one_eye",
    "folded_ponytail", "side_ponytail", "low-tied_long_hair", "twin_braids",
    "front_braid", "french_braid", "single_braid", "crown_braid",
}
HAIR_ACCESSORY_EXACT = {
    "hair_ornament", "hair_bow", "hair_ribbon", "hairband", "hair_flower",
    "hairclip", "hair_tie", "hair_bobbles", "hair_scrunchy", "hair_ring",
    "hair_net", "hair_covering", "hair_on_horn", "hair_pin", "hair_stick",
}

EYES_EXACT = {
    "heterochromia", "eyelashes", "eyelash", "colored_eyelashes", "long_eyelashes",
    "thick_eyelashes", "eyelid_pull", "half-closed_eye", "half-closed_eyes",
    "one_eye_closed", "tareme", "tsurime", "jitome", "empty_eyes", "glowing_eyes",
    "sparkling_eyes", "heart-shaped_pupils", "symbol-shaped_pupils", "slit_pupils",
    "constricted_pupils", "dilated_pupils", "cross-eyed", "wall-eyed", "rolling_eyes",
    "eye_contact", "eye_reflection", "eye_focus", "eyeball", "no_eyes", "solid_eyes",
    "colored_sclera", "black_sclera", "bright_pupils", "glowing_eye",
}

FACE_EXACT = {
    "smile", "grin", "smirk", "frown", "open_mouth", "closed_mouth", "parted_lips",
    "blush", "light_blush", "heavy_blush", "nose_blush", "tears", "crying",
    "streaming_tears", "teary_eyes", "tears_of_joy", "angry", "annoyed", "sad",
    "happy", "surprised", "scared", "embarrassed", "pout", "wink", "one_eyebrow_raised",
    "eyebrows", "thick_eyebrows", "eyeliner", "eyeshadow", "makeup", "lipstick",
    "tongue", "tongue_out", "licking_lips", "biting_lip", "drooling", "saliva",
    "teeth", "fangs", "skin_fang", "single_fang", "nose", "mouth", "lips",
    "expressionless", "serious", "determined", "confident", "smug", "evil_smile",
    "crazy_smile", "forced_smile", "wakame_(expression)", "3:", "^_^", ":d", ":o",
    ":p", ":q", ":3", ";)", ":|", ">:(", ">_<", "t_t", "x_x", "o_o", "uwu", "owo",
    "clenched_teeth", "gritted_teeth", "furrowed_brow", "sweatdrop", "sweat",
    "character_birthday", "facepalm",
}

BODY_EXACT = {
    "breasts", "large_breasts", "huge_breasts", "gigantic_breasts", "small_breasts",
    "flat_chest", "medium_breasts", "cleavage", "underboob", "sideboob",
    "navel", "midriff", "stomach", "abs", "toned", "muscular", "muscular_female",
    "muscular_male", "collarbone", "neck", "throat", "shoulders", "wide_shoulders",
    "narrow_waist", "wide_hips", "hips", "thighs", "thick_thighs", "plump",
    "skin", "dark_skin", "pale_skin", "tan", "tanlines", "freckles", "mole",
    "mole_under_eye", "beauty_mark", "body_fur", "chest_hair", "armpit",
    "armpits", "bare_shoulders", "bare_arms", "bare_legs", "bare_foot", "barefoot",
    "feet", "foot", "toes", "bare_toes", "fingers", "fingernails", "toenails",
    "nail_polish", "hands", "hand", "hand_on_hip", "legs", "long_legs",
    "spread_legs", "crossed_legs", "knees", "knee", "elbow", "waist", "torso",
    "back", "spine", "ribs", "butt", "ass", "wide_hips", "curvy", "petite",
    "tall_female", "short_female", "chubby", "fat", "slim", "skinny",
}

CLOTHING_EXACT = {
    "dress", "skirt", "shirt", "t-shirt", "blouse", "sweater", "hoodie", "jacket",
    "coat", "cardigan", "vest", "tank_top", "camisole", "crop_top", "tube_top",
    "halterneck", "off-shoulder", "sleeveless", "long_sleeves", "short_sleeves",
    "puffy_sleeves", "detached_sleeves", "wide_sleeves", "fur_trim", "frills",
    "lace", "ribbon", "bow", "bowtie", "necktie", "ascot", "scarf", "muffler",
    "pants", "jeans", "shorts", "short_shorts", "hot_pants", "leggings",
    "thighhighs", "thigh_highs", "pantyhose", "stockings", "socks", "kneehighs",
    "tabi", "garter_belt", "garter_straps", "legwear", "footwear", "shoes",
    "boots", "high_heels", "sandals", "sneakers", "loafers", "mary_janes",
    "slippers", "barefoot", "gloves", "fingerless_gloves", "arm_warmers",
    "elbow_gloves", "opera_gloves", "mittens", "swimsuit", "bikini", "one-piece_swimsuit",
    "school_swimsuit", "competition_swimsuit", "micro_bikini", "sling_bikini",
    "wedding_dress", "evening_gown", "kimono", "yukata", "hanfu", "qipao",
    "sari", "dirndl", "robe", "cloak", "cape", "poncho", "apron", "overalls",
    "dungarees", "suspender_skirt", "corset", "bodysuit", "leotard", "unitard",
    "tracksuit", "jersey", "sports_bra", "bandeau", "sarong", "pareo", "loincloth",
    "underwear", "panties", "boxers", "briefs", "lingerie", "bra", "bralette",
    "camisole", "slip_(clothing)", "nightgown", "pajamas", "sleepwear",
    "sarashi", "bandages", "armband", "legband", "thigh_band", "garter",
    "plaid", "striped", "polka_dot", "floral", "checkered", "argyle",
    "denim", "leather", "latex", "silk", "velvet", "fur", "knit", "mesh",
    "pleated_skirt", "pencil_skirt", "tiered_skirt", "suspender", "belt",
    "sash", "obi", "waistcoat", "suit", "tuxedo", "business_suit", "blazer",
}

UNIFORM_EXACT = {
    "school_uniform", "serafuku", "sailor_dress", "sailor_collar", "blazer_uniform",
    "gym_uniform", "track_uniform", "sports_uniform", "military_uniform",
    "police_uniform", "nurse_uniform", "maid_uniform", "maid", "waitress",
    "cheerleader", "cheerleader_uniform", "kimono_uniform", "band_uniform",
    "flight_attendant", "stewardess", "office_lady", "business_suit",
    "shrine_maiden", "miko", "nun", "nun_habit", "witch_hat", "wizard",
    "labcoat", "lab_coat", "hazmat_suit", "spacesuit", "armor", "plate_armor",
    "knight", "samurai", "ninja", "shinobi", "bodysuit", "power_armor",
    "police", "soldier", "firefighter", "doctor", "surgeon", "chef", "barista",
    "baseball_uniform", "soccer_uniform", "basketball_uniform", "tennis_uniform",
    "swimming_uniform", "kendo", "judo", "karate", "gakuran", "sailor_suit",
    # 更多职业 / 身份
    "nurse", "teacher", "student", "schoolgirl", "schoolboy", "office_worker",
    "salaryman", "waiter", "cook", "baker", "bartender", "farmer", "fisherman",
    "hunter", "archer", "paladin", "priest", "priestess", "monk", "mage",
    "sorcerer", "sorceress", "warlock", "assassin", "thief", "pirate",
    "ronin", "gunslinger", "cowboy", "detective", "scientist", "researcher",
    "engineer", "pilot", "captain", "sailor", "general", "king", "queen",
    "prince", "princess", "noble", "butler", "nanny", "bodyguard", "guard",
    "police_officer", "paramedic", "lifeguard", "athlete", "coach", "referee",
    "idol", "singer", "dancer", "actor", "model", "photographer", "journalist",
    "librarian", "cashier", "receptionist", "secretary", "programmer",
    "hacker", "gamer", "streamer", "vtuber", "witch", "alchemist", "blacksmith",
    "merchant", "innkeeper", "bartender_girl", "magical_girl", "superhero",
    "supervillain", "mecha_pilot", "spy", "agent", "explorer", "archaeologist",
    "astronaut", "diver", "miner", "carpenter", "painter", "sculptor",
    "musician", "conductor", "nun_(clothing)", "yukata", "hakama", "miko_outfit",
    "sailor", "seifuku", "gym_shorts", "bloomers", "buruma",
}

ACCESSORY_EXACT = {
    "hat", "cap", "baseball_cap", "beret", "fedora", "top_hat", "bowler_hat",
    "sun_hat", "straw_hat", "witch_hat", "santa_hat", "cone_hat", "beanie",
    "hood", "veil", "crown", "tiara", "headband", "headphones", "earphones",
    "glasses", "sunglasses", "eyepatch", "eye_patch", "monocle", "goggles",
    "mask", "surgical_mask", "mouth_mask", "face_mask", "scarf", "necklace",
    "choker", "pendant", "locket", "earrings", "earring", "hoop_earrings",
    "stud_earrings", "bracelet", "bangle", "wristband", "watch", "wristwatch",
    "ring", "rings", "brooch", "badge", "pin", "button", "medal", "armband",
    "apron", "backpack", "bag", "handbag", "purse", "satchel", "school_bag",
    "shoulder_bag", "umbrella", "parasol", "fan", "hand_fan", "hair_ornament",
    "hair_bow", "hair_ribbon", "hairband", "hair_flower", "hairclip", "hair_tie",
    "hair_bobbles", "hair_scrunchy", "hair_ring", "hair_pin", "hair_stick",
    "bell", "collar", "leash", "tail_ornament", "wing_ornament", "antennae",
    "horns", "animal_ears", "cat_ears", "dog_ears", "fox_ears", "rabbit_ears",
    "wolf_ears", "fake_animal_ears", "wig", "fake_horns", "beard", "mustache",
    "bandaid", "bandage", "plaster", "cast", "crutch", "headset", "visor",
    "hairband", "kerchief", "bandana", "neckerchief", "ascot",
}

POSE_EXACT = {
    "standing", "sitting", "kneeling", "lying", "on_back", "on_stomach", "on_side",
    "squatting", "crouching", "walking", "running", "jumping", "dancing",
    "leaning_forward", "leaning_back", "arms_up", "arms_behind_back", "arms_behind_head",
    "arms_crossed", "crossed_arms", "hand_on_hip", "hands_on_hips", "hand_up",
    "hand_on_own_chest", "hand_on_own_face", "hand_on_own_hip", "hand_on_own_head",
    "hand_on_own_knee", "hand_on_own_leg", "hand_on_own_arm", "hand_on_own_cheek",
    "hands_on_own_chest", "holding", "holding_sword", "holding_book", "holding_cup",
    "holding_flower", "holding_umbrella", "holding_staff", "holding_weapon",
    "hugging", "hug", "hugging_doll", "carrying", "carrying_person", "piggyback",
    "peace_sign", "v_sign", "thumbs_up", "pointing", "pointing_at_viewer",
    "waving", "salute", "stretching", "yawning", "sleeping", "eating", "drinking",
    "reading", "writing", "sitting_on_chair", "sitting_on_ground", "seiza",
    "indian_style", "wariza", "straddling", "bent_over", "arched_back",
    "head_tilt", "outstretched_arm", "outstretched_hand", "reaching_out",
    "reaching_towards_viewer", "clenched_hand", "clenched_fist", "fist",
    "open_hand", "palm", "folded_arms", "hand_in_hair", "hand_in_own_hair",
    "holding_hands", "interlocked_fingers", "paw", "covering_face", "covering_mouth",
    "covering_ears", "shushing", "phone", "looking_at_viewer", "looking_away",
    "looking_back", "looking_down", "looking_up", "looking_to_the_side",
    "eye_contact", "staring", "glaring", "winking", "flying", "floating",
    "swimming", "riding", "horseback_riding", "sitting_on_lap", "lap_pillow",
    "head_rest", "head_on_hand", "chin_rest", "facepalm", "shrugging",
    "stretching_arms", "bowing", "curtsy", "crawling", "prone", "supine",
}

SCENE_EXACT = {
    "indoors", "outdoors", "bedroom", "living_room", "kitchen", "bathroom",
    "classroom", "school", "hallway", "library", "cafe", "restaurant",
    "office", "hospital", "church", "shrine", "temple", "castle", "palace",
    "ruins", "street", "city", "cityscape", "town", "village", "rooftop",
    "balcony", "window", "door", "wall", "floor", "ceiling", "stairs",
    "bed", "on_bed", "chair", "table", "desk", "sofa", "couch", "bench",
    "bookshelf", "wardrobe", "mirror", "bathtub", "shower", "pool", "swimming_pool",
    "beach", "ocean", "sea", "lake", "river", "waterfall", "pond", "underwater",
    "forest", "woods", "tree", "trees", "garden", "park", "field", "meadow",
    "mountain", "hill", "cliff", "valley", "desert", "island", "cave",
    "sky", "cloud", "clouds", "cloudy_sky", "blue_sky", "night_sky", "starry_sky",
    "star_(sky)", "star", "stars", "moon", "full_moon", "sun", "sunset",
    "sunrise", "horizon", "scenery", "landscape", "background", "simple_background",
    "white_background", "black_background", "grey_background", "gradient_background",
    "transparent_background", "solid_background", "blurry_background",
    "detailed_background", "abstract_background", "checkered_floor",
    "space", "outer_space", "planet", "earth_(planet)", "galaxy", "nebula",
    "starfish", "spacecraft", "window_(wall)", "curtains", "curtain",
    "fence", "railing", "bridge", "road", "path", "train", "train_station",
    "car", "vehicle", "bicycle", "motorcycle", "boat", "ship", "airplane",
    "sign", "signpost", "lamp_post", "streetlight", "neon_lights", "billboard",
}

NATURE_EXACT = {
    "spring_(season)", "summer", "autumn", "fall", "winter", "season", "seasons",
    "snow", "snowing", "snowfall", "snowflake", "snowflakes", "ice", "icicle",
    "frost", "blizzard", "rain", "raining", "raindrops", "rainbow", "storm",
    "thunder", "lightning", "fog", "mist", "haze", "wind", "breeze", "cloudy",
    "sunny", "overcast", "cherry_blossoms", "sakura", "petals", "falling_petals",
    "flower", "flowers", "flower_field", "sunflower", "rose", "tulip", "lily",
    "lotus", "hydrangea", "wisteria", "maple_leaf", "autumn_leaves", "fallen_leaves",
    "leaf", "leaves", "grass", "bush", "branch", "vine", "moss", "mushroom",
    "butterfly", "firefly", "dragonfly", "bee", "bird", "birds", "seagull",
    "feather", "feathers", "bubble", "bubbles", "sparkle", "sparkles", "glitter",
    "stardust", "light_particles", "particles", "dust", "smoke", "steam",
}

# 更宽泛的"包含即命中"规则（放在精确规则之后）
CAMERA_SUBSTR = (
    "from_above", "from_below", "from_behind", "from_side", "from_outside",
    "from_between", "close-up", "wide_shot", "full_body", "upper_body",
    "lower_body", "cowboy_shot", "portrait", "dutch_angle", "perspective",
    "vanishing_point", "depth_of_field", "blurry", "motion_blur", "focus",
    "foreshortening", "panorama", "fish_eye", "macro", "aerial_view",
    "birds_eye_view", "worms_eye_view", "third_person", "first_person",
    "pov", "profile", "three_quarter", "back_view", "front_view",
    "symmetry", "symmetrical", "framing", "composition", "aspect_ratio",
    "letterboxed", "border", "frame", "cropped", "out_of_frame",
    "head_out_of_frame", "feet_out_of_frame", "cutoff", "zoomed_in",
    "looking_at_hand", "camera", "photography", "selfie", "mirror_selfie",
    "holding_camera", "shotgun", "bokeh", "chromatic_aberration", "lens_flare",
    "vignetting", "grain", "film_grain", "scan", "high_speed_photography",
    "long_exposure", "polaroid", "screenshot", "multiple_views", "reference_sheet",
    "character_sheet", "turnaround", "outline", "lineart", "sketch",
)

LIGHTING_SUBSTR = (
    "lighting", "backlighting", "backlit", "rim_light", "rim_lighting",
    "volumetric", "god_rays", "sunbeam", "sunlight", "moonlight", "starlight",
    "candlelight", "firelight", "neon", "glow", "glowing", "glowstick",
    "shadow", "shadows", "cast_shadow", "silhouette", "contrast", "high_contrast",
    "chiaroscuro", "golden_hour", "blue_hour", "twilight", "dusk", "dawn",
    "lens_flare", "light_rays", "light_particles", "spotlight", "floodlight",
    "soft_lighting", "hard_lighting", "ambient_occlusion", "subsurface_scattering",
    "bloom", "hdr", "overexposed", "underexposed", "reflection", "reflections",
    "monochrome", "greyscale", "grayscale", "sepia", "pastel_colors",
    "colorful", "vibrant", "muted_colors", "warm_colors", "cool_colors",
    "limited_palette", "color_palette", "gradient", "iridescent", "holographic",
    "opalescent", "pearlescent", "saturated", "desaturated", "duotone",
    "red_theme", "blue_theme", "green_theme", "pink_theme", "purple_theme",
    "yellow_theme", "orange_theme", "black_theme", "white_theme", "aqua_theme",
)

STYLE_EXACT = {
    "anime", "anime_coloring", "anime_style", "manga", "comic", "cartoon",
    "chibi", "realistic", "photorealistic", "semi-realistic", "3d", "3d_(artwork)",
    "cel_shading", "flat_color", "flat_shading", "soft_shading", "watercolor",
    "oil_painting", "acrylic_painting", "gouache", "pastel", "charcoal",
    "pencil", "ink", "inktober", "calligraphy", "brushstroke", "sumi-e",
    "ukiyo-e", "art_nouveau", "art_deco", "impressionism", "surrealism",
    "cubism", "pop_art", "minimalism", "abstract", "abstract_art",
    "pixel_art", "voxel", "8-bit", "16-bit", "vector", "vector_art",
    "low_poly", "clay", "claymore", "sculpture", "papercraft", "origami",
    "stained_glass", "mosaic", "collage", "graffiti", "sticker", "poster",
    "sketch", "rough_sketch", "lineart", "monochrome_lineart", "colored_lineart",
    "traditional_media", "digital_painting", "concept_art", "illustration",
    "official_style", "fan_art", "ai-generated", "cyberpunk", "steampunk",
    "dieselpunk", "retrofuturism", "vaporwave", "synthwave", "art_station",
    "guofeng", "chinese_style", "japanese_style", "gothic", "baroque",
    "renaissance", "rococo", "romanticism", "expressionism", "pointillism",
    "storybook", "children_s_book", "silhouette_art", "negative_space",
    "fake_screenshot", "album_cover", "movie_poster", "book_cover", "icon",
    "logo", "emblem", "crest", "coat_of_arms", "map", "chart", "diagram",
}

# 生物：按「词元」匹配，避免 turtle→turtleneck、bunny→playboy_bunny 这类误伤
CREATURE_TOKENS = {
    "cat", "cats", "dog", "dogs", "fox", "wolf", "rabbit", "bunny", "bird",
    "birds", "dragon", "horse", "bear", "mouse", "rat", "deer", "lion", "tiger",
    "panda", "penguin", "whale", "dolphin", "shark", "fish", "octopus", "squid",
    "jellyfish", "snake", "lizard", "frog", "spider", "insect", "bee",
    "butterfly", "dinosaur", "phoenix", "griffin", "unicorn", "pegasus",
    "slime", "fairy", "angel", "demon", "devil", "ghost", "spirit", "zombie",
    "skeleton", "monster", "kaiju", "robot", "android", "cyborg", "mecha",
    "golem", "pokemon", "creature", "animal", "animals", "kemonomimi",
    "nekomimi", "catgirl", "catboy", "foxgirl", "wolfgirl", "kitsune",
    "tanuki", "oni", "yokai", "mermaid", "elf", "dwarf", "orc", "vampire",
    "werewolf", "succubus", "incubus", "goblin", "troll", "giant", "nymph",
    "centaur", "harpy", "lamia", "arachne", "drider", "sphinx", "chimera",
    "hippogriff", "wyvern", "kraken", "leviathan", "behemoth", "familiar",
}
CREATURE_GUARD = {
    "playboy_bunny", "bunny_suit", "bunny_ears", "cat_suit", "dog_suit",
    "cat_ears", "dog_ears", "fox_ears", "rabbit_ears", "wolf_ears",
    "horse_ears", "animal_ears", "turtleneck", "catsuit", "cat_lingerie",
    "bear_ears", "mouse_ears", "tiger_ears", "lion_ears",
}

# 题材 / 世界观：同样改成词元匹配（"art" 之类的子串会误伤 parted_bangs）
THEME_TOKENS = {
    "fantasy", "magic", "magical", "spell", "spells", "wizard", "witch",
    "sorcery", "sorceress", "cyber", "cyberpunk", "futuristic", "apocalypse",
    "post-apocalyptic", "steampunk", "dieselpunk", "industrial", "historical",
    "medieval", "victorian", "edo", "feudal", "war", "warfare", "battle",
    "military", "adventure", "journey", "romance", "romantic", "slice_of_life",
    "school_life", "idol", "concert", "festival", "matsuri", "fireworks",
    "hanabi", "christmas", "halloween", "valentine", "new_year", "birthday",
    "wedding", "party", "celebration", "holiday", "vacation", "travel",
    "camping", "sports", "music", "band", "dance", "dancing", "singing",
    "gaming", "video_game", "board_game", "cooking", "tea_party", "reading",
    "horror", "mystery", "detective", "noir", "utopia", "dystopia", "dream",
    "nightmare", "afterlife", "heaven", "hell", "underworld", "mythology",
    "norse", "greek", "religion", "religious", "buddhism", "shinto",
    "christianity", "occult", "tarot", "zodiac", "constellation", "astrology",
    "alchemy", "potion", "grimoire", "isekai", "supernatural", "paranormal",
    "tradition", "traditional", "ceremony", "ritual", "folklore", "legend",
    "fairy_tale", "nursery_rhyme", "circus", "carnival", "amusement_park",
    "cafe", "maid_cafe", "aquarium", "zoo", "museum", "library", "onsen",
    "hot_spring", "bathhouse", "school_festival", "culture_festival",
    "sports_festival", "graduation", "entrance_ceremony", "hanami",
    "tanabata", "obon", "setsubun", "hinamatsuri", "children_s_day",
}

# 物品道具：词元匹配，"note"→"notebook" 这类仍然保留少量安全子串
OBJECT_TOKENS = {
    "sword", "katana", "dagger", "knife", "spear", "lance", "bow", "arrow",
    "arrows", "axe", "hammer", "staff", "wand", "scythe", "gun", "pistol",
    "rifle", "shotgun", "shield", "armor", "helmet", "book", "books",
    "notebook", "letter", "envelope", "pen", "pencil", "brush", "palette",
    "easel", "canvas", "cup", "mug", "glass", "bottle", "teacup", "teapot",
    "plate", "bowl", "fork", "spoon", "chopsticks", "food", "cake", "bread",
    "candy", "chocolate", "apple", "fruit", "vegetable", "rice", "noodle",
    "ramen", "sushi", "burger", "pizza", "coffee", "tea", "juice", "drink",
    "balloon", "gift", "present", "box", "basket", "lantern", "candle",
    "lamp", "chandelier", "clock", "hourglass", "key", "lock", "chain",
    "rope", "net", "hook", "mirror", "comb", "towel", "soap", "perfume",
    "lipstick", "phone", "smartphone", "cellphone", "computer", "laptop",
    "keyboard", "monitor", "television", "radio", "speaker", "headphones",
    "microphone", "camera", "tripod", "controller", "console", "arcade",
    "joystick", "dice", "card", "cards", "chess", "shogi", "puzzle", "doll",
    "plush", "plushie", "toy", "toys", "ball", "kite", "banner", "flag",
    "sign", "signpost", "poster", "painting", "photograph", "vase", "plant",
    "broom", "mop", "bucket", "ladder", "tool", "wrench", "screwdriver",
    "chainsaw", "syringe", "scalpel", "microscope", "telescope", "binoculars",
    "map", "compass", "globe", "backpack", "suitcase", "luggage", "crate",
    "barrel", "bag", "purse", "wallet", "jewelry", "gem", "gemstone",
    "crystal", "diamond", "pearl", "coin", "money", "treasure", "crown",
    "ring", "necklace", "music", "guitar", "piano", "violin", "drum",
    "flute", "trumpet", "headset", "umbrella", "parasol", "fan", "pillow",
    "cushion", "blanket", "towel", "ribbon", "string", "thread", "needle",
    "scissors", "tape", "paper", "newspaper", "magazine", "cardboard_box",
}
OBJECT_SUBSTR = ("_sword", "_book", "_toy", "_doll", "_ball", "plushie")


def tokens_of(tag: str) -> list[str]:
    return tag.split("_")


def make_predicates():
    """构造有序的 (分类, 判定函数) 列表。"""

    def ex(store):
        return lambda tag, toks: tag in store

    def tok(store):
        return lambda tag, toks: any(t in store for t in toks)

    def sub(store):
        return lambda tag, toks: any(s in tag for s in store)

    people_tokens = {
        "1girl", "1boy", "2girls", "2boys", "3girls", "3boys", "4girls", "4boys",
        "5girls", "5boys", "6girls", "6boys", "multiple_girls", "multiple_boys",
        "solo", "duo", "group", "crowd", "male_focus", "female_focus",
        "male", "female", "personification", "twins", "siblings", "child",
        "adult", "teenager", "elderly", "old", "young", "baby", "toddler",
        "genderbend", "crossdressing", "trap", "otoko_no_ko", "futanari",
        "androgynous", "bishounen", "bishoujo", "kemonomimi", "humanization",
    }
    people_re = re.compile(r"^\d+\+?girls?$|^\d+\+?boys?$")

    rules = [
        ("quality", ex(QUALITY_EXACT)),
        ("r18", lambda tag, toks: tag in R18_EXACT),
        ("r18", lambda tag, toks: tag in R18_GUARD and False),
        ("r18", lambda tag, toks: tag not in R18_GUARD and any(t in R18_TOKENS for t in toks)),
        ("people", lambda tag, toks: tag in people_tokens or bool(people_re.match(tag))),
        ("hair", ex(HAIR_EXACT)),
        ("hair", lambda tag, toks: "hair" in tag and tag not in HAIR_ACCESSORY_EXACT),
        ("eyes", ex(EYES_EXACT)),
        ("eyes", lambda tag, toks: tag.endswith("_eyes") or tag == "eyes"
         or tag.endswith("_eye") and tag not in ("eye_patch", "eye_contact")),
        ("face", ex(FACE_EXACT)),
        ("face", lambda tag, toks: any(t in {"eyebrow", "eyebrows", "eyelash",
                                             "eyelashes", "eyeliner", "eyeshadow",
                                             "lipstick", "makeup", "blush",
                                             "mouth", "lips", "teeth", "tongue",
                                             "nose", "fangs", "fang", "drool",
                                             "saliva", "tears", "sweatdrop"}
                                       for t in toks)),
        ("uniform", ex(UNIFORM_EXACT)),
        ("accessory", ex(ACCESSORY_EXACT)),
        ("accessory", lambda tag, toks: any(
            t in {"ornament", "earring", "earrings", "necklace", "choker",
                  "bracelet", "bangle", "wristband", "brooch", "pendant",
                  "goggles", "vest", "suspenders"}
            for t in toks)),
        ("clothing", ex(CLOTHING_EXACT)),
        ("clothing", lambda tag, toks: any(
            t in {"dress", "skirt", "shirt", "sweater", "hoodie", "jacket", "coat",
                  "cardigan", "kimono", "yukata", "uniform", "suit", "tie",
                  "necktie", "bowtie", "scarf", "socks", "stockings", "boots",
                  "shoes", "sandals", "gloves", "cape", "cloak", "apron",
                  "corset", "leotard", "swimsuit", "bikini", "lingerie",
                  "underwear", "panties", "bra", "belt", "sash", "robe"}
            for t in toks)),
        ("body", ex(BODY_EXACT)),
        ("body", lambda tag, toks: any(
            t in {"breast", "breasts", "bust", "navel", "abs", "muscle", "muscles",
                  "skin", "thigh", "thighs", "leg", "legs", "arm", "arms",
                  "hand", "hands", "finger", "fingers", "foot", "feet", "toe",
                  "toes", "waist", "hip", "hips", "shoulder", "shoulders",
                  "neck", "back", "chest", "belly", "stomach", "butt", "ass",
                  "eye_bags", "wrinkle", "wrinkles"}
            for t in toks)),
        ("pose", ex(POSE_EXACT)),
        ("pose", lambda tag, toks: any(
            t in {"holding", "sitting", "standing", "walking", "running",
                  "jumping", "lying", "kneeling", "leaning", "looking",
                  "reaching", "hugging", "carrying", "pointing", "waving",
                  "crossed", "spread", "raised", "outstretched", "clenched",
                  "stretching", "dancing", "riding", "crawling", "bowing",
                  "salute", "shrugging", "yawning", "sleeping", "eating",
                  "drinking", "reading", "writing", "playing",
                  "hand_on", "hands_on", "sitting_on", "lying_on", "on_bed",
                  "on_chair", "on_ground", "on_lap", "piggyback"}
            for t in toks)),
        # 画风要排在相机/构图之前，否则 lineart / sketch 会被相机规则抢走
        ("style", ex(STYLE_EXACT)),
        ("style", lambda tag, toks: any(
            t in {"art", "artwork", "artstyle", "style", "painting", "drawing",
                  "rendering", "shading", "palette", "aesthetic", "realism",
                  "impressionism", "surrealism", "minimalism", "abstract"}
            for t in toks)),
        ("camera", sub(CAMERA_SUBSTR)),
        ("lighting", sub(LIGHTING_SUBSTR)),
        ("scene", ex(SCENE_EXACT)),
        ("scene", lambda tag, toks: any(
            t in {"room", "house", "building", "buildings", "street", "station",
                  "shop", "store", "cafe", "restaurant", "kitchen", "bathroom",
                  "bedroom", "temple", "castle", "tower", "gate", "wall",
                  "window", "curtain", "curtains", "floor", "ceiling",
                  "furniture", "table", "desk", "chair", "bed", "sofa", "couch",
                  "bench", "shelf", "bookshelf", "mirror", "stairs", "staircase",
                  "door", "doorway", "rooftop", "balcony", "garden", "park",
                  "bridge", "road", "path", "fence", "city", "cityscape",
                  "town", "village", "indoors", "outdoors", "background",
                  "interior", "exterior", "ruins", "dungeon", "lab",
                  "laboratory", "hospital", "office", "classroom", "school",
                  "shrine", "church", "palace", "space", "planet", "vehicle",
                  "train", "car", "bus", "boat", "ship", "airplane", "bicycle"}
            for t in toks)),
        ("nature", ex(NATURE_EXACT)),
        ("nature", lambda tag, toks: any(
            t in {"sky", "cloud", "clouds", "star", "stars", "moon", "sun",
                  "sunset", "sunrise", "horizon", "forest", "woods", "tree",
                  "trees", "flower", "flowers", "grass", "leaf", "leaves",
                  "mountain", "hill", "valley", "cliff", "river", "lake",
                  "ocean", "sea", "beach", "island", "desert", "cave",
                  "waterfall", "pond", "underwater", "snow", "rain", "wind",
                  "fog", "mist", "storm", "lightning", "thunder", "rainbow",
                  "summer", "winter", "spring", "autumn", "season", "weather",
                  "nature", "landscape", "scenery", "petal", "petals", "plant",
                  "plants", "bush", "branch", "vine", "moss", "mushroom",
                  "bubble", "bubbles", "sparkle", "sparkles", "feather",
                  "feathers", "galaxy", "nebula", "aurora", "eclipse"}
            for t in toks)),
        ("object", ex(OBJECT_TOKENS)),
        ("object", sub(OBJECT_SUBSTR)),
        ("theme", ex(THEME_TOKENS)),
        ("theme", lambda tag, toks: any(
            t in {"fantasy", "magical", "magic", "mythology", "legend", "legendary"}
            for t in toks)),
        # 生物放最后，前面已经消化掉服装/配饰里的 cat_ears、turtleneck 之类
        ("creature", lambda tag, toks: tag not in CREATURE_GUARD
         and any(t in CREATURE_TOKENS for t in toks)),
    ]
    return rules


RULES = make_predicates()


def classify(tag: str, danbooru_cat: int) -> str | None:
    """返回标签所属分类 id；None 表示不进核心库。"""
    if danbooru_cat == D_CHARACTER:
        return "character"
    if danbooru_cat == D_COPYRIGHT:
        return "series"
    if danbooru_cat == D_ARTIST:
        return "artist"
    if danbooru_cat == D_META:
        return "meta"
    toks = tokens_of(tag)
    for cat, predicate in RULES:
        try:
            if predicate(tag, toks):
                return cat
        except Exception:
            continue
    return None


def is_r18(tag: str, danbooru_cat: int) -> int:
    # 排除表优先，避免误伤 bondage_pants / analog / sexual_harassment 这类标签
    if tag in R18_GUARD:
        return 0
    if tag in R18_EXACT:
        return 1
    toks = tokens_of(tag)
    return 1 if any(t in R18_TOKENS for t in toks) else 0


# ---------------------------------------------------------------------------
# 别名
# ---------------------------------------------------------------------------
def load_aliases(path: Path) -> dict[str, list[str]]:
    """从 danbooru.csv 读取英文别名表。"""
    out: dict[str, list[str]] = {}
    if not path.exists():
        print(f"  ! 找不到别名文件 {path}，跳过别名", file=sys.stderr)
        return out
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if len(row) < 4:
                continue
            tag = row[0].strip()
            raw = row[3].strip()
            if not tag or not raw:
                continue
            aliases = [a.strip().replace(" ", "_") for a in raw.split(",") if a.strip()]
            aliases = [a for a in aliases if a.lower() != tag.lower()]
            if aliases:
                out[tag.lower()] = aliases[:8]
    return out


def normalize_key(tag: str) -> str:
    return tag.replace(" ", "_").lower()


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def build(input_dir: Path, output_dir: Path) -> int:
    supermarket = input_dir / "supermarket.json"
    if not supermarket.exists():
        print(f"[错误] 找不到输入文件 {supermarket}", file=sys.stderr)
        return 1
    print(f"[1/4] 读取 {supermarket} ...")
    rows = json.loads(supermarket.read_text(encoding="utf-8"))
    print(f"      共 {len(rows):,} 条标签")

    aliases = load_aliases(input_dir / "danbooru.csv")
    print(f"      别名表 {len(aliases):,} 条")

    # ---- 分类
    print("[2/4] 分类 + R18 判定 ...")
    core_pool: dict[str, list[tuple]] = defaultdict(list)
    full_lines: list[str] = []
    r18_count = 0
    cat_counter = Counter()
    r18_by_cat = Counter()

    for row in rows:
        if len(row) < 4:
            continue
        en, zh, dcat, count = row[0], row[1], int(row[2]), int(row[3])
        if not en:
            continue
        flag = is_r18(en, dcat)
        if flag:
            r18_count += 1
        cat = "r18" if flag else classify(en, dcat)
        # 画师投稿量太低的直接不进全量检索，避免 14 万条噪音
        if dcat == D_ARTIST and count < 100:
            continue
        alias = ",".join(aliases.get(en.lower(), []))
        full_lines.append(f"{en}\t{zh}\t{dcat}\t{flag}\t{count}\t{alias}")
        if cat is not None:
            core_pool[cat].append((en, zh, count, flag))
            cat_counter[cat] += 1
            if flag:
                r18_by_cat[cat] += 1

    # ---- 核心库
    print("[3/4] 生成核心库 ...")
    # 补上手工整理的提示词词条（masterpiece / bad_hands 之类不是 Danbooru 标签的词）
    injected = 0
    core_names = {r[0] for pool in core_pool.values() for r in pool}
    for cid, extras in EXTRA_PROMPT_TAGS.items():
        for en, zh in extras:
            if en in core_names:
                continue
            core_pool[cid].append((en, zh, 0, 0))
            core_names.add(en)
            injected += 1
    print(f"      手工补充提示词 {injected} 条")

    categories = []
    total_core = 0
    report = {}
    for cid, name in CATEGORY_ORDER:
        cap = CORE_CAPS.get(cid, 500)
        pool = core_pool.get(cid, [])
        # 按投稿量降序；R18 排到最后，这样关掉 R18 时截断也不会影响主体
        pool.sort(key=lambda r: (r[3], -r[2]))
        picked = pool[:cap]
        # 排序：非 R18 按热度，R18 整体沉底
        picked.sort(key=lambda r: (r[3], -r[2]))
        categories.append({
            "id": cid,
            "name": name,
            "tags": [[r[0], r[1], r[2], r[3]] for r in picked],
        })
        total_core += len(picked)
        report[cid] = (name, len(picked), len(pool))

    output_dir.mkdir(parents=True, exist_ok=True)
    core_path = output_dir / "tags_core.json"
    core_path.write_text(json.dumps({
        "version": 1,
        "generated": date.today().isoformat(),
        "source": "Danbooru tag dataset (317k, zh-translated)",
        "categories": categories,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print("[4/4] 生成全量索引 ...")
    full_path = output_dir / "tags_full.tsv.gz"
    with gzip.open(full_path, "wt", encoding="utf-8", compresslevel=6) as fh:
        fh.write("\n".join(full_lines))
        fh.write("\n")

    # ---- 报告
    print()
    print("=" * 66)
    print(f"核心库合计 {total_core:,} 个标签，全量索引 {len(full_lines):,} 行")
    print(f"R18 标记 {r18_count:,} 个")
    print("-" * 66)
    print(f"{'分类':<14}{'名称':<12}{'核心':>8}{'候选':>9}")
    for cid, name in CATEGORY_ORDER:
        n, picked, pool = report[cid][1], report[cid][1], report[cid][2]
        print(f"{cid:<14}{name:<12}{picked:>8}{pool:>9}")
    print("-" * 66)

    # 抽样
    print("\n每类抽样（前 8 个）:")
    for cat in categories:
        sample = ", ".join(f"{t[0]}({t[1]})" for t in cat["tags"][:8])
        print(f"  [{cat['id']}] {sample}")

    print("\nR18 抽样（前 40 个）:")
    r18_tags = next((c for c in categories if c["id"] == "r18"), {"tags": []})
    print("  " + ", ".join(t[0] for t in r18_tags["tags"][:40]))

    print("\n文件大小:")
    print(f"  {core_path}  {core_path.stat().st_size / 1024:.0f} KB")
    print(f"  {full_path}  {full_path.stat().st_size / 1024 / 1024:.1f} MB")
    return 0


def verify(output_dir: Path) -> int:
    """对生成结果做自检。"""
    print("\n" + "=" * 66)
    print("自检")
    print("-" * 66)
    ok = True
    core_path = output_dir / "tags_core.json"
    full_path = output_dir / "tags_full.tsv.gz"

    data = json.loads(core_path.read_text(encoding="utf-8"))
    seen: dict[str, str] = {}
    dup = 0
    for cat in data["categories"]:
        for t in cat["tags"]:
            if t[0] in seen:
                dup += 1
                if dup <= 5:
                    print(f"  ! 重复标签 {t[0]} 出现在 {seen[t[0]]} 与 {cat['id']}")
            seen[t[0]] = cat["id"]
    print(f"  核心标签去重: {'通过' if dup == 0 else f'失败（{dup} 个重复）'}")
    ok &= dup == 0

    checks = [
        ("hatsune_miku", "character"), ("long_hair", "hair"), ("twintails", "hair"),
        ("blue_eyes", "eyes"), ("smile", "face"), ("school_uniform", "uniform"),
        ("sitting", "pose"), ("outdoors", "scene"), ("thighhighs", "clothing"),
        ("sword", "object"), ("masterpiece", "quality"), ("highres", "meta"),
        ("bad_hands", "quality"), ("masterpiece", "quality"),
    ]
    for tag, want in checks:
        got = seen.get(tag)
        state = "OK " if got == want else "!! "
        if got != want:
            ok = False
        print(f"  {state}{tag:<16} 期望 {want:<10} 实际 {got}")

    with gzip.open(full_path, "rt", encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().split("\n") if ln]
    bad = [ln for ln in lines[:5000] if len(ln.split("\t")) != 6]
    print(f"  全量索引 {len(lines):,} 行，列数检查: {'通过' if not bad else '失败'}")
    ok &= not bad

    print("-" * 66)
    print("自检结果:", "全部通过 ✓" if ok else "存在问题 ✗")
    return 0 if ok else 1


def default_input_dir() -> Path:
    """依次尝试 <项目>/.work、<项目>/../.work、当前目录/.work。"""
    for cand in (ROOT / ".work", ROOT.parent / ".work", Path.cwd() / ".work"):
        if (cand / "supermarket.json").exists():
            return cand
    return ROOT / ".work"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 ComfyUI_TagSelect 的标签数据")
    parser.add_argument("--input-dir", default=str(default_input_dir()))
    parser.add_argument("--output-dir", default=str(ROOT / "assets" / "data"))
    parser.add_argument("--skip-verify", action="store_true")
    args = parser.parse_args()

    code = build(Path(args.input_dir), Path(args.output_dir))
    if code == 0 and not args.skip_verify:
        code = verify(Path(args.output_dir))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
