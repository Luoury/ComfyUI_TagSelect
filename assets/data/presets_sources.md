# ComfyUI_TagSelect 预设库来源

本文件记录 `presets.json` 中每个分组/重点预设实际参考并抓取过的来源。所有链接均为本次实际用 `curl` 抓取成功的页面（`web_fetch` 对 `docs.novelai.net` 与 `huggingface.co` 报“解析到非公网 IP”，故改用 `curl`）。

## 数据与拼写基准

- 本地标签数据集 `/home/luosury/Code/DSH_Test/.work/supermarket.json`（317,423 行 `[english, chinese, category, post_count]`）。
  - 用于：所有普通条目的 danbooru 拼写校验与规范化（小写 + 空格转下划线），并据此修正 `clouds→cloud`、`stars→star`、`side_view→from_side`、`spring→spring_(season)`、`sci-fi→science_fiction`、`retro_futurism→retrofuturism`、`clones→clone`、`url→web_address`、`adult→mature_female`、`simple_shading→soft_shading`、`clean_background→simple_background`、`sunbeams→sunbeam`、`extra_digit→extra_digits` 等。

## quality / 画质与质量

- [NovelAI Documentation — Add Quality Tags Toggle](https://docs.novelai.net/en/image/qualitytags)
  - 用于：各版本 NovelAI 官方质量标签串（V1/V2/V3/V4/V4.5/V5 的 `best quality, amazing quality, very aesthetic, absurdres` 等），以及 `{{}}` 加权形式的合法来源。
- [AUTOMATIC1111 WebUI Wiki — Features（Attention/emphasis）](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features)
  - 用于：A1111 权重语法 `(word:1.5)` / `[word]` 的确切行为，以及「NAI 的 `{}` 相当于 1.05 倍、`[]` 相当于 0.952 倍」的换算依据，写进 `quality_aesthetic_weighted`、`model_sdxl` 的说明与条目。
- [stable-diffusion-v1-5 官方模型卡](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/raw/main/README.md)
  - 用于：SD1.5 底模基本信息，支撑 `model_sd15` / `quality_sd15_legacy` 的适用模型说明。
- [SDXL Base 1.0 官方模型卡](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/raw/main/README.md)
  - 用于：SDXL 原生 1024 分辨率与架构说明，支撑 `model_sdxl` 的分辨率注意事项。

## model / 模型专用

- [NovelAI Documentation — Add Quality Tags Toggle](https://docs.novelai.net/en/image/qualitytags)
  - 用于：`model_nai_v3`（Anime V3 质量串）、`model_nai_v4`（V4 Full：`no text, best quality, very aesthetic, absurdres`）、`model_nai_v4_5`（V4.5 Full：`location, very aesthetic, masterpiece, no text`）、`model_nai_v5`（V5：`very aesthetic, masterpiece, no text`）。
- [NovelAI Documentation — Undesired Content](https://docs.novelai.net/en/image/undesiredcontent)
  - 用于：各版本官方 UC 负面预设原文 —— V3 Heavy（`lowres, {bad}, error, fewer, extra, missing, ...`）、V4 Heavy、V4.5 Full Heavy、V5 Light（含 `0::ai-generated::` 数值强调写法），以及经典 `Low Quality + Bad Anatomy` 串。
- [NovelAI Documentation — Tagging](https://docs.novelai.net/en/image/tags)
  - 用于：NovelAI 标签体系与质量标签追加位置（V3 加在末尾）等说明。
- [NoobAI-XL v-pred 0.5 模型卡（Hugging Face）](https://huggingface.co/Laxhar/noobai-XL-Vpred-0.5/raw/main/README.md)
  - 用于：`model_noobai_vpred` 的官方 Prompt Prefix（`masterpiece, best quality, newest, absurdres, highres, safe`）、官方 Negative Prompt、CFG/步数/采样器/Euler 与 832x1216 等参数要求，以及质量标签表（masterpiece / best quality / good quality / …）与 `very awa` 美学标签。
- [NoobAI-XL 1.0 (eps) 模型卡（Hugging Face）](https://huggingface.co/Laxhar/noobai-XL-1.0/raw/main/README.md)
  - 用于：`model_noobai_eps` 的官方 Prompt Prefix 与 Negative Prompt（与 v-pred 版一致的推荐串）。
- [Illustrious-XL v1.0 模型卡（Hugging Face）](https://huggingface.co/OnomaAIResearch/Illustrious-XL-v1.0/raw/main/README.md)
  - 用于：`model_illustrious_xl` 的模型特性说明（1536×1536 原生分辨率、Danbooru 标签 + 自然语言混合提示、知识截止 2024-06）。
- [Illustrious-xl-early-release-v0 模型卡（Hugging Face）](https://huggingface.co/OnomaAIResearch/Illustrious-xl-early-release-v0/raw/main/README.md)
  - 用于：Illustrious 系谱与许可/基座关系（NoobAI 自称微调自该模型）的交叉确认。
- [Pony Diffusion V6 XL — 模型页（CivitArchive 镜像）](https://civitaiarchive.com/models/257749?modelVersionId=290640)
  - 用于：`model_pony_v6_xl` / `model_pony_v6_negative` 的官方默认模板 `score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up`、`source_pony/source_furry/source_cartoon/source_anime` 与 `rating_safe/rating_questionable/rating_explicit`，以及「需 clip skip 2、多数情况不需要负面提示词」的官方说明。
- [Pony Diffusion V6 XL 模型卡（Hugging Face 镜像）](https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL/raw/main/README.md)
  - 用于：交叉确认 Pony V6 的 score 串与 `clip skip 2` 要求（示例 widget 即使用完整 score 串 + `source_furry`）。

## style / 画风风格

- 本地 danbooru 数据集：确认媒介类标签的规范写法，如 `watercolor_(medium)`、`oil_painting_(medium)`、`ink_(medium)`、`ukiyo-e`、`pixel_art`、`8-bit`、`flat_color`、`retro_artstyle`、`1980s_(style)`、`cel_rendering`、`cyberpunk`、`chinese_clothes`、`hanfu`。
- [NovelAI Documentation — Undesired Content](https://docs.novelai.net/en/image/undesiredcontent)（Furry Focus 预设中的 `[flat colors]`、`chromatic aberration` 等风格类词条参考）
- [AUTOMATIC1111 WebUI Wiki — Features](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features)（Booru 标签/媒介词在提示词中的使用与转义说明）

## lighting / 光影氛围

- [NovelAI Documentation — Undesired Content](https://docs.novelai.net/en/image/undesiredcontent)（`chromatic aberration`、`film grain`、`dithering`、`halftone` 等光影/画面质感类负面词条）
- 本地 danbooru 数据集：确认 `backlighting`、`light_rays`、`bloom`、`lens_flare`、`depth_of_field`、`motion_blur`、`golden_hour`、`chiaroscuro`、`candlelight`、`moonlight`、`sunlight`、`neon_sign` 等真实标签；`cinematic lighting`、`rim light`、`volumetric lighting`、`god rays`、`soft lighting` 等经查不存在于数据集，作为自由提示词短语保留并在校验报告中列明。

## composition / 构图视角

- 本地 danbooru 数据集：确认 `portrait`、`full_body`、`upper_body`、`cowboy_shot`、`close-up`、`wide_shot`、`dutch_angle`、`from_above`、`from_below`、`from_side`、`from_behind`、`profile`、`foreshortening`、`contrapposto`、`looking_back` 等规范标签，并据此把 `side_view` 修正为 `from_side`。
- [NovelAI Documentation — Tagging](https://docs.novelai.net/en/image/tags)（标签顺序对构图/质量的影响）

## scenario / 场景题材

- 本地 danbooru 数据集：确认 `classroom`、`school_uniform`、`serafuku`、`cherry_blossoms`、`summer_festival`、`yukata`、`fireworks`、`shrine`、`torii`、`starry_sky`、`star_(sky)`、`milky_way`、`cafe`、`beach`、`autumn_leaves`、`maple_leaf`、`rooftop`、`cyberpunk`、`cityscape`、`neon_sign` 等场景标签。
- [NoobAI-XL v-pred 0.5 模型卡](https://huggingface.co/Laxhar/noobai-XL-vpred-0.5/raw/main/README.md)（日期标签 `newest`/`recent` 与 `year xxxx` 用法，用于场景的时代感控制）

## character / 角色模板

- 本地 danbooru 数据集：确认初音未来套装全部条目 `hatsune_miku`、`vocaloid`、`twintails`、`aqua_hair`、`aqua_eyes`、`detached_sleeves`、`necktie`、`thighhighs`、`hair_ornament`、`headphones`，以及 `magical_girl`、`plate_armor`、`kimono`、`obi`、`cyberware`、`visor` 等角色服饰标签；据此修正 `school_girl`→`school_uniform`、`silver_hair`→`grey_hair`、`japanese_style`→删除（改用 `japanese_clothes`/`obi`）。
- [Pony Diffusion V6 XL 模型卡](https://huggingface.co/LyliaEngine/Pony_Diffusion_V6_XL/raw/main/README.md)（角色/物种标签与 `source_*` 组合方式）

## negative / 负面提示词

- [NovelAI Documentation — Undesired Content](https://docs.novelai.net/en/image/undesiredcontent)
  - 用于：`neg_low_quality`、`neg_text_watermark` 等块的词条选型；官方 `Low Quality + Bad Anatomy` 串（`lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry`）直接支撑 `neg_general`。
- [NovelAI Documentation — Add Quality Tags Toggle](https://docs.novelai.net/en/image/qualitytags)（`no text`、`rating:general` 等官方排除项）
- [NoobAI-XL v-pred 0.5 模型卡](https://huggingface.co/Laxhar/noobai-XL-Vpred-0.5/raw/main/README.md)（`mutated hands`、`worst quality`、`signature`、`username`、`logo` 等负面词条）
- [Pony Diffusion V6 XL — 模型页](https://civitaiarchive.com/models/257749?modelVersionId=290640)（`score_4/5/6` 与 `source_*` 作为负面压制手段）
- 本地 danbooru 数据集：确认 `bad_hands`、`bad_anatomy`、`missing_fingers`、`extra_digits`、`fewer_digits`、`deformed`、`bad_feet`、`extra_legs`、`jpeg_artifacts`、`watermark`、`artist_logo`、`web_address`、`speech_bubble`、`completely_nude`、`nipples`、`mosaic_censoring`、`bar_censor` 等真实标签；`fused_fingers`、`malformed_hands`、`polydactyly`、`missing_arms/legs`、`extra_heads` 等经查不存在，作为自由于负面短语保留并单独说明。

## 诚实说明（未能验证的部分）

- `docs.novelai.net` 与 `huggingface.co` 无法通过 `web_fetch` 访问（工具报“解析到非公网 IP”），上述内容均以 `curl` 抓取原文获得，链接可直接打开核对。
- `danbooru.donmai.us/wiki_pages/tag_group:image_composition` 与 `stable-diffusion-art.com/sdxl-prompts/` 抓取被 Cloudflare 的 JS 挑战拦截，未能取到正文；因此构图类标签改用本地 danbooru 数据集逐条核对，未引用该两处。
- **SD1.5 / SDXL 的“动漫质量串”并非官方文档规定**：官方模型卡只描述架构与分辨率。`masterpiece, best quality` + `extremely detailed CG unity 8k wallpaper` 与 `(worst quality, low quality:1.4)` 属于社区长期通用写法，本库按社区事实标准收录并在预设 `desc` 中注明。
- Illustrious 的 `masterpiece, best quality, very aesthetic, absurdres` 同样属于 Illustrious/NoobAI 系的社区通用写法（NoobAI 模型卡有官方质量标签表作为旁证），Illustrious 官方卡本身未给出该推荐串。
- `Pony V6 XL` 的负面词（`score_4/5/6` + `source_*`）为社区惯用做法：官方明确表示该模型多数情况下不需要负面提示词，本库据此在预设说明中标注。
