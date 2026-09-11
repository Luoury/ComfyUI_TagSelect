# -*- coding: utf-8 -*-
"""标签数据库：核心分类数据 + 全量检索索引。"""

from __future__ import annotations

import gzip
import json
import threading
from typing import Iterable

from .qtcompat import QtCore, Signal
from .resources import DATA_DIR

CORE_FILE = DATA_DIR / "tags_core.json"
FULL_FILE = DATA_DIR / "tags_full.tsv.gz"

# 画师标签数量极多且实用性低，只保留有一定投稿量的
MIN_ARTIST_COUNT = 100

CAT_ARTIST = 1
CAT_SERIES = 3
CAT_CHARACTER = 4

CJK_RANGE = ("\u3400", "\u9fff")

def has_cjk(text: str) -> bool:
    for ch in text:
        if CJK_RANGE[0] <= ch <= CJK_RANGE[1] or "\u3040" <= ch <= "\u30ff":
            return True
    return False

class Tag:
    """轻量标签对象（用于 UI 传递）。"""

    __slots__ = ("en", "zh", "count", "r18", "cat", "custom")

    def __init__(self, en: str, zh: str, count: int = 0, r18: int = 0,
                 cat: str = "all", custom: bool = False) -> None:
        self.en = en
        self.zh = zh or ""
        self.count = count
        self.r18 = r18
        self.cat = cat
        self.custom = custom

    @property
    def key(self) -> str:
        return self.en

    def __repr__(self) -> str:  # pragma: no cover
        return f"Tag({self.en!r}, {self.zh!r}, {self.count}, r18={self.r18})"

class Category:
    __slots__ = ("id", "name", "tags")

    def __init__(self, cid: str, name: str, tags: list[Tag]) -> None:
        self.id = cid
        self.name = name
        self.tags = tags

    def __repr__(self) -> str:  # pragma: no cover
        return f"Category({self.id}, {self.name}, {len(self.tags)})"

# 搜索优先级
_R_EXACT, _R_PREFIX, _R_CONTAIN, _R_ALIAS, _R_ZH, _R_ZH_CONTAIN = 0, 1, 2, 3, 4, 5

class TagDatabase(QtCore.QObject):
    """标签数据。核心数据同步加载，全量索引后台加载。"""

    fullIndexReady = Signal()
    fullIndexFailed = Signal(str)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.categories: list[Category] = []
        self._by_id: dict[str, Category] = {}
        self.hot: list[Tag] = []
        self.error: str | None = None

        self._full: list[tuple] | None = None       # (en, zh, cat, r18, count, aliases)
        self._full_en: list[str] | None = None      # 小写英文，检索用
        self._loading = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------ 加载
    @property
    def full_ready(self) -> bool:
        return self._full is not None

    @property
    def loading(self) -> bool:
        return self._loading

    @property
    def full_count(self) -> int:
        return len(self._full) if self._full else 0

    def load_core(self) -> None:
        """同步加载核心分类数据（启动时调用）。"""
        if not CORE_FILE.exists():
            self.error = f"缺少数据文件：{CORE_FILE}"
            return
        with CORE_FILE.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)

        cats: list[Category] = []
        for item in raw.get("categories", []):
            tags = [
                Tag(row[0], row[1], int(row[2]), int(row[3]), item["id"])
                for row in item.get("tags", [])
            ]
            cats.append(Category(item["id"], item["name"], tags))
        self.categories = cats
        self._by_id = {c.id: c for c in cats}
        self._build_hot()

    def _build_hot(self) -> None:
        """热门标签：跨分类按投稿量取头部（用于"全部"页）。"""
        seen: set[str] = set()
        pool: list[Tag] = []
        for cat in self.categories:
            if cat.id in ("r18", "artist"):
                continue
            for tag in cat.tags:
                if tag.r18 or tag.en in seen:
                    continue
                seen.add(tag.en)
                pool.append(tag)
        pool.sort(key=lambda t: -t.count)
        self.hot = pool[:600]

    def load_full_async(self) -> None:
        if self._loading or self._full is not None:
            return
        self._loading = True
        threading.Thread(target=self._load_full_worker, name="tag-full-index", daemon=True).start()

    def _load_full_worker(self) -> None:
        try:
            rows: list[tuple] = []
            en_lower: list[str] = []
            with gzip.open(FULL_FILE, "rt", encoding="utf-8") as fh:
                for line in fh:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) < 6:
                        continue
                    en, zh, cat, r18, count, alias = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
                    try:
                        cat_i = int(cat)
                        r18_i = int(r18)
                        cnt_i = int(count)
                    except ValueError:
                        continue
                    if cat_i == CAT_ARTIST and cnt_i < MIN_ARTIST_COUNT:
                        continue
                    rows.append((en, zh, cat_i, r18_i, cnt_i, alias.lower()))
                    en_lower.append(en.lower())
            with self._lock:
                self._full = rows
                self._full_en = en_lower
        except Exception as exc:  # pragma: no cover
            self._loading = False
            self.fullIndexFailed.emit(str(exc))
            return
        self._loading = False
        self.fullIndexReady.emit()

    # ------------------------------------------------------------ 查询
    def category(self, cid: str) -> Category | None:
        return self._by_id.get(cid)

    def tags_for(self, cid: str, include_r18: bool) -> list[Tag]:
        if cid == "all":
            base = self.hot
        else:
            cat = self._by_id.get(cid)
            base = cat.tags if cat else []
        if include_r18 or cid == "r18":
            return base
        return [t for t in base if not t.r18]

    def all_tag_names(self) -> set[str]:
        names: set[str] = set()
        for cat in self.categories:
            for t in cat.tags:
                names.add(t.en)
        if self._full:
            names.update(r[0] for r in self._full)
        return names

    def lookup(self, english: str) -> Tag | None:
        """按英文名查标签（用于把预设里的 tag 变成结构化对象）。"""
        low = english.lower()
        for cat in self.categories:
            for t in cat.tags:
                if t.en.lower() == low:
                    return t
        if self._full:
            for row in self._full:
                if row[0].lower() == low:
                    return Tag(row[0], row[1], row[4], row[3], self._cat_id(row[2]))
        return None

    @staticmethod
    def _cat_id(danbooru_cat: int) -> str:
        return {
            CAT_ARTIST: "artist",
            CAT_SERIES: "series",
            CAT_CHARACTER: "character",
            5: "meta",
        }.get(danbooru_cat, "other")

    def search(self, query: str, limit: int = 400, include_r18: bool = False,
               category: str | None = None) -> list[Tag]:
        """中英混合搜索。

        先搜核心库（快），全量索引就绪后自动覆盖全库。
        category 不为 None 时只在该分类内搜索。
        """
        q = query.strip()
        if not q:
            return []
        q_low = q.lower()
        q_us = q_low.replace(" ", "_")
        zh_query = has_cjk(q)

        results: list[tuple[int, int, Tag]] = []
        seen: set[str] = set()

        def consider(tag: Tag, alias: str = "") -> None:
            if not include_r18 and tag.r18:
                return
            if tag.en in seen:
                return
            seen.add(tag.en)
            en = tag.en.lower()
            if en == q_us or en == q_low:
                rank = _R_EXACT
            elif en.startswith(q_us):
                rank = _R_PREFIX
            elif q_us in en or q_low in en:
                rank = _R_CONTAIN
            elif alias and (q_us in alias or q_low in alias):
                rank = _R_ALIAS
            elif tag.zh and q in tag.zh:
                rank = _R_ZH if tag.zh.startswith(q) else _R_ZH_CONTAIN
            else:
                return
            results.append((rank, -tag.count, tag))

        # 1) 核心分类库
        for cat in self.categories:
            if category and cat.id != category:
                continue
            for tag in cat.tags:
                consider(tag)
                if len(results) > limit * 6:
                    break

        # 2) 全量库
        if self._full and self._full_en is not None:
            rows = self._full
            lows = self._full_en
            n = len(rows)
            for i in range(n):
                if len(results) > limit * 8:
                    break
                en_low = lows[i]
                hit = False
                if zh_query:
                    if q_us in en_low or q in rows[i][1]:
                        hit = True
                else:
                    if q_us in en_low or q_low in en_low:
                        hit = True
                    elif rows[i][5] and q_us in rows[i][5]:
                        hit = True
                    elif q in rows[i][1]:
                        hit = True
                if not hit:
                    continue
                row = rows[i]
                consider(Tag(row[0], row[1], row[4], row[3], self._cat_id(row[2])), row[5])

        results.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in results[:limit]]

    def stats(self) -> dict:
        return {
            "core": sum(len(c.tags) for c in self.categories),
            "categories": len(self.categories),
            "full": self.full_count,
            "full_ready": self.full_ready,
        }

def merge_tags(*groups: Iterable[Tag]) -> list[Tag]:
    """按顺序合并去重（保持先后顺序）。"""
    seen: set[str] = set()
    out: list[Tag] = []
    for group in groups:
        for tag in group:
            if tag.en in seen:
                continue
            seen.add(tag.en)
            out.append(tag)
    return out

def tags_from_names(names, db: "TagDatabase | None" = None) -> list[Tag]:
    """把预设里的字符串（可能带权重括号）转成 Tag 对象用于展示。"""
    out: list[Tag] = []
    seen: set[str] = set()
    for raw in names:
        text = str(raw).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        found = db.lookup(text) if db is not None else None
        if found is not None:
            out.append(found)
        else:
            out.append(Tag(text, "", 0, 0, "preset"))
    return out
