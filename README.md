# 学习资源站 · xuexi.devmini.space

考试 / 学习 / 办公 三方向的夸克网盘资料索引站。纯静态，托管在 GitHub Pages。

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

## 数据管道（搬运路径）

```
目标站发现资源 → 提取原始 quark_url
   → quark_batch_run.py 转存到我的夸克网盘 + 生成永久分享链接
   → scripts/publish_resources.py 合并进 data/resources.json（按 quark_url 的 md5 幂等）
   → scripts/build_sitemap.py 重建 sitemap.xml / robots.txt
   → git push → GitHub Pages 自动部署
```

### 转存 + 分享（复用 quark-mswnlz-publisher）

```bash
# 在 QuarkPanTool 环境执行（幂等键 = quark_url 的 md5 前 12 位）
python3 scripts/quark_batch_run.py --month 202610 \
  --items-json items.json --out-json batch_share_results.json
```

`items.json`：

```json
[{"title": "2026国考行测真题", "url": "https://pan.quark.cn/s/xxxx"}]
```

### 写库 + 上线（本站脚本）

```bash
python3 scripts/publish_resources.py \
  --items items.json \
  --shares batch_share_results.json \
  --push
```

### 只重建 sitemap

```bash
python3 scripts/build_sitemap.py
```

> 站点**不做分类页预生成**（SEO 靠 sitemap 按需更新 + 数据入库即重建）。后续数据量上来再考虑预渲染。

## 分类

| 大类 | 子类 |
|------|------|
| 考试 | 国考 / 省考 / 事业编 / 教师资格 / 考研 / 四六级 / 职业资格 |
| 学习 | 中小学 / 大学课程 / 语言学习 / 编程技术 / AI 学习 / 电子书 |
| 办公 | Excel / Word / PPT / 简历求职 / 合同文书 / 述职总结 |

## 部署

- 自定义域名：`xuexi.devmini.space`（`CNAME` 文件已就位）
- Pages 分支：`main` / 根目录
- 每次 push 自动部署

## 免责

本站仅整理公开分享信息，不存储任何资源文件。详见 `disclaimer.html`。
