# 学习资料站 · xuexi.devmini.space

考试真题 / 中小学资料 / 办公素材 三类夸克网盘资源索引。纯静态，托管在 GitHub Pages。

## 目录结构

```
index.html          首页（搜索 + 分类筛选 + 资源流）
category.html       分类浏览   ?c=exam|study|office  &s=<子类>
search.html         搜索结果   ?q=<关键词>
resource.html       资料详情   ?id=<资源 id>
about.html          关于本站
disclaimer.html     免责声明
data/taxonomy.json  分类定义（三大类 + 子类）
data/resources.json 资源库（唯一数据源）
assets/             样式 + 前端逻辑
scripts/            数据管道
```

## 分类（按源站真实家底设定）

| 大类 | 子类 | 源站实际可用量 |
|------|------|------|
| **考试真题** | 高考真题 / 中考真题 / 数学 / 语文 / 英语 / 物理 / 化学 | 高考 7,208 + 中考 6,526 |
| **中小学资料** | 小学 / 初中 / 高中 / 大学 / 试卷 / 知识点 | 50,904 |
| **办公素材** | PPT 模板 / 简历求职 / 述职总结 / 教学课件 / Excel / 合同文书 | 办公素材网格 + 搜索索引 |

> 注：源站**没有**成规模的国考/省考/事业编/教资/考研/四六级资源，故不再设这些类目。

## 数据管道（搬运路径）

```
源站分类页 / API 列表 → 拿 slug
   → 详情页取 pan.quark.cn 原始链接
   → quark_batch_run.py 转存到我的夸克网盘 + 生成永久分享链接
   → scripts/publish_resources.py 合并进 data/resources.json（按 quark_url 的 md5 幂等）
   → scripts/build_sitemap.py 重建 sitemap.xml / robots.txt
   → git push → GitHub Pages 自动部署
```

### 源站数据端点（`api.quarksource.com`）

| 端点 | 用途 |
|------|------|
| `/learning/exam-papers?exam=gaokao\|zhongkao` | 高考 / 中考真题列表 |
| `/learning/k12/items` | 中小学资料列表（grade / subject / type / edition / semester） |
| `/media` | 影视（本站不收录） |

### 转存 + 分享（复用 quark-mswnlz-publisher）

```bash
python3 scripts/quark_batch_run.py --items-json items.json --out-json batch_share_results.json
```

`items.json`：`[{"title": "...", "url": "https://pan.quark.cn/s/xxxx"}]`

### 写库 + 上线（本站脚本）

```bash
python3 scripts/publish_resources.py --items items.json --shares batch_share_results.json --push
python3 scripts/build_sitemap.py   # 仅重建 sitemap
```

## 部署

- 自定义域名：`xuexi.devmini.space`（`CNAME` 已就位）
- Pages：`main` 分支 / 根目录，每次 push 自动部署

## 免责

本站仅整理公开分享信息，不存储任何资源文件。详见 `disclaimer.html`。
