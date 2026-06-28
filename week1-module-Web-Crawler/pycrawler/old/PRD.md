# 快递物流政策与寄递规则采集系统 PRD

## 1. 项目概述

本项目建设一个面向快递物流公开政策、寄递规则、服务条款与特殊品类运输要求的合规采集系统。系统从中国邮政及国内外主流快递物流企业、监管机构、行业组织的公开页面中采集结构化资料，形成可检索、可追溯、可对比的数据集，为后续规则问答、政策检索、企业规则横向对比和知识库建设提供基础数据。

项目重点不只是抓取网页，而是建立一套可审计的数据采集流程：每条数据都需要保留来源 URL、抓取时间、正文版本、适用范围、政策主题、原文证据和解析状态，确保数据来源真实、规则可追踪、采集行为可审计。

## 2. 目标与非目标

### 2.1 目标

- 覆盖中国邮政、EMS、顺丰、京东物流、三通一达、极兔、德邦、跨越、菜鸟等国内主要快递物流企业。
- 覆盖 UPS、FedEx、DHL、USPS、Royal Mail、Japan Post、Australia Post、Canada Post、新加坡邮政等海外及国际物流主体。
- 覆盖国家邮政局、交通运输、海关、民航、铁路、万国邮联、IATA 等监管和行业规则来源。
- 重点采集禁限寄、危险品、易碎品、活体动物、冷藏冷冻、生鲜、医药、锂电池、国际清关、邮寄保险、保价赔付、延误赔偿、包装要求、实名寄递、投诉处理等政策。
- 形成标准化数据字段，支持按公司、国家/地区、运输方式、品类、政策主题和更新时间进行筛选。
- 严格遵守公开访问规则、合理限速和来源标注要求。

### 2.2 非目标

- 不采集登录后、付费后、内部系统、个人隐私或非公开数据。
- 不绕过验证码、登录限制、访问控制、IP 封禁或反爬机制。
- 不进行高频请求、压力测试或影响目标站点正常服务的行为。
- 不把采集结果直接解释为法律意见，系统只做公开规则归档和引用。

## 3. 用户与使用场景

### 3.1 主要用户

- 物流政策研究人员：查询不同企业、不同国家/地区的寄递规则差异。
- 业务运营人员：快速确认特殊品类是否可寄、如何包装、是否需要附加材料。
- 客服与审核人员：根据公开政策定位原文证据，辅助解释赔付、禁限寄、时效和服务争议。
- 数据与算法人员：构建快递物流规则知识库、检索增强问答和规则分类模型。

### 3.2 典型场景

- 查询“顺丰、EMS、FedEx 对锂电池寄递的限制有什么不同”。
- 查询“冷冻食品跨省寄递需要哪些包装和温控要求”。
- 查询“国际件寄送化妆品、液体、粉末、药品时是否受限制”。
- 查询“活体动物、植物、种子、昆虫样本是否允许寄递，以及适用例外”。
- 查询“易碎品破损后，各公司保价赔付和责任限制规则”。
- 查询“国内保价服务和国际声明价值、运输保险之间的差异，以及不同承运商的赔付上限”。
- 查询“危险品空运、陆运、国际运输分别引用哪些监管规则”。
- 查询“中国邮政、UPS、FedEx、DHL 的海关申报与清关资料要求”。

## 4. 采集范围

### 4.1 国内快递与物流企业

| 类别 | 企业/平台 | 重点采集内容 |
| --- | --- | --- |
| 邮政体系 | 中国邮政、EMS、中国邮政国际业务 | 禁限寄目录、国内/国际寄递规则、实名寄递、邮寄保险、保价赔付、时限标准、邮政普遍服务、国际邮件清关 |
| 直营快递 | 顺丰速运、京东物流、跨越速运、德邦快递 | 寄件须知、托寄物限制、包装规范、邮寄保险、保价赔付、时效产品、冷运、医药物流、大件物流、航空件限制 |
| 加盟快递 | 圆通、申通、中通、韵达、极兔、百世、安能 | 禁限寄规则、服务协议、赔付规则、投诉处理、异常件处理、网点服务规则 |
| 电商物流 | 菜鸟、抖音电商物流规则、拼多多物流规则、京东开放平台物流规则 | 平台发货规则、物流服务承诺、超时/延误判责、违规商品寄递限制 |
| 同城即时 | 顺丰同城、闪送、达达、UU 跑腿、美团配送 | 同城禁运品、贵重物品、鲜花蛋糕、生鲜冷链、活体/宠物限制、异常赔付 |

### 4.2 海外与国际物流主体

| 地区 | 企业/机构 | 重点采集内容 |
| --- | --- | --- |
| 全球快递 | UPS、FedEx、DHL Express、TNT | Dangerous Goods、Lithium Batteries、Terms and Conditions、Service Guide、Customs、Surcharges、Packaging |
| 美国 | USPS、US DOT/PHMSA、FAA、CBP | Mailing Standards、Hazardous Materials、International Mail Manual、海关申报、航空危险品限制 |
| 欧洲 | Royal Mail、La Poste、Deutsche Post DHL、PostNL | Prohibited and restricted items、国际邮寄、海关、危险品、电池、食品和植物限制 |
| 亚太 | Japan Post、Korea Post、Singapore Post、Australia Post、New Zealand Post | EMS 国际规则、禁限寄、海关、危险品、生鲜食品和动植物检疫 |
| 加拿大 | Canada Post、CBSA | Non-mailable matter、国际寄递、清关、危险品与赔偿条款 |

### 4.3 监管、行业与标准来源

| 来源 | 重点采集内容 |
| --- | --- |
| 国家邮政局 | 禁寄物品指导目录、实名收寄、快递市场管理、服务标准、投诉申诉规则 |
| 海关总署 | 进出境邮件快件监管、个人物品限值、申报要求、动植物检疫、食品药品限制 |
| 交通运输部 | 道路运输、冷链运输、危险货物运输相关公开规则 |
| 中国民用航空局 | 航空运输危险品、锂电池、充电宝、液体粉末等限制 |
| 国家市场监督管理总局/标准委 | 快递服务、冷链物流、包装、绿色包装、服务质量相关标准信息 |
| 万国邮联 UPU | 国际邮件、EMS、禁限寄协作、跨境邮政服务规则 |
| IATA | Dangerous Goods Regulations、Lithium Battery Guidance、航空危险品分类 |
| WCO/各国海关 | 国际清关、HS 编码、申报资料、进出口限制 |

## 5. 重点政策主题

### 5.1 禁限寄与危险品

- 爆炸品、压缩气体、易燃液体、易燃固体、氧化剂、有毒物质、腐蚀品、放射性物质、磁性物质。
- 化工品、油漆、胶水、酒精、消毒液、香水、喷雾、干冰、气雾罐、农药、实验试剂。
- 锂电池、充电宝、带电设备、纯电池、纽扣电池、铅酸电池。
- 枪支弹药、管制刀具、仿真武器、警用装备。
- 毒品、麻醉药品、精神药品、处方药、违禁出版物。
- 现金、有价证券、贵金属、珠宝、文物、重要证件等高价值或限制物品。

### 5.2 易碎品与高价值物品

- 玻璃、陶瓷、精密仪器、电子屏幕、手表、艺术品、收藏品。
- 包装要求：缓冲材料、内外包装、木架、抗压、防震、防潮标识。
- 验视要求、保价规则、破损责任、免责条款、理赔材料。
- 是否接受“仅外包装完好但内物破损”的赔付申请。

### 5.3 活体、动植物与生物样本

- 活体动物、宠物、鱼虾蟹、水族生物、昆虫、蚕种、蜂群。
- 植物、种子、苗木、土壤、微生物、菌种。
- 血液、尿液、组织样本、医学检测样本、生物制品。
- 检疫证明、运输资质、包装容器、温控要求、是否允许邮寄。

### 5.4 冷藏冷冻与生鲜医药

- 生鲜食品、水果、肉类、水产、乳制品、蛋糕、鲜花。
- 冷藏、冷冻、恒温、干冰、冰袋、泡沫箱、温控记录。
- 医药冷链：疫苗、胰岛素、检测试剂、药品、医疗器械。
- 时效承诺、温度区间、异常处置、破损/变质赔付。

### 5.5 国际寄递与清关

- 禁运国家/地区、目的国限制、制裁规则、承运商服务暂停。
- 商业发票、运单、报关单、HS 编码、原产地、税费说明。
- 食品、药品、化妆品、液体粉末、电子产品、品牌商品、个人物品限制。
- 退运、扣关、销毁、补资料、税费承担、清关延误责任。

### 5.6 服务条款与赔付

- 运费、燃油附加费、偏远地区附加费、超长超重费、住宅派送费。
- 保价、声明价值、责任限制、免责条款、赔付上限。
- 延误、丢失、破损、短少、错分、退回、拒收、无人签收。
- 投诉、仲裁、证据材料、处理时限、申诉渠道。

### 5.7 邮寄保险、保价与声明价值

- 国内快递常见保价服务：保价费率、最低收费、最高保价金额、足额保价、不足额保价、未保价赔付规则。
- 国际快递常见声明价值：Declared Value for Carriage、Declared Value for Customs、Carrier Liability、Shipment Insurance 的区别。
- 赔付触发条件：丢失、破损、短少、污染、延误、温控异常、退运、扣关、不可抗力。
- 保险或保价排除项：现金、有价证券、珠宝、古董、艺术品、文物、易碎品、生鲜、药品、活体、危险品、二手电子产品等。
- 理赔材料：运单、发票、交易凭证、价值证明、破损照片、外包装照片、签收证明、检测报告、温控记录。
- 理赔期限：索赔提交时限、承运商处理时限、补充材料时限、复议或申诉渠道。
- 责任限制：按运费倍数赔付、按重量赔付、按声明价值赔付、按保价金额赔付、最高责任限额。
- 跨境规则：国际公约、目的国法律、海关扣留、禁限运导致的保险免责或责任限制。

## 6. 数据字段设计

### 6.1 原始页面字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `source_id` | string | 来源唯一 ID |
| `company` | string | 企业或机构名称 |
| `source_type` | enum | 企业官网、监管机构、行业组织、平台规则、PDF、公告 |
| `country_region` | string | 国家/地区 |
| `url` | string | 原始 URL |
| `canonical_url` | string | 规范化 URL |
| `title` | string | 页面标题 |
| `published_at` | date | 发布日期 |
| `updated_at` | date | 更新时间 |
| `crawled_at` | datetime | 抓取时间 |
| `content_hash` | string | 正文哈希，用于去重和版本管理 |
| `raw_html_path` | string | 原始 HTML 保存路径 |
| `text_path` | string | 清洗文本保存路径 |
| `screenshot_path` | string | 必要时保存页面截图 |

### 6.2 规则解析字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `policy_category` | enum | 禁限寄、危险品、易碎品、冷链、活体、赔付、清关、包装、服务条款等 |
| `item_category` | string | 物品类别，如锂电池、药品、生鲜、玻璃制品 |
| `transport_mode` | enum | 国内陆运、国内航空、国际快递、邮政 EMS、冷链、同城 |
| `permission_status` | enum | 可寄、限制寄递、禁止寄递、需人工确认 |
| `requirements` | array | 包装、证明、申报、温控、保价等要求 |
| `liability_rule` | text | 赔付或免责规则摘要 |
| `insurance_available` | boolean | 是否存在邮寄保险、保价或声明价值服务 |
| `insurance_type` | enum | 保价、运输保险、声明价值、承运商责任、第三方保险、未知 |
| `insurance_fee_rule` | text | 保价或保险费用计算规则 |
| `declared_value_limit` | text | 声明价值或保价金额上限 |
| `compensation_limit` | text | 赔付上限、按重量赔付或按运费倍数赔付规则 |
| `claim_deadline` | text | 索赔或理赔提交时限 |
| `claim_materials` | array | 理赔所需材料 |
| `insurance_exclusions` | array | 保险或保价免责物品、免责场景 |
| `evidence_text` | text | 原文关键证据片段 |
| `evidence_url` | string | 证据页面 URL |
| `confidence` | enum | 高、中、低，表示解析可靠性 |
| `review_status` | enum | 待审核、已审核、需复查 |

## 7. 访问控制与限速策略

### 7.1 页面范围控制

1. 只采集明确公开、无需登录、非个人化的页面与文档。
2. 禁止抓取搜索结果页、登录页、购物下单页、个人信息页、运单跟踪页、价格实时查询接口等高敏或非政策类页面。
3. 对首页、导航聚合页、资讯页、帮助中心页和营销页做过滤，不作为训练样本。
4. 若页面出现验证码、访问控制、权限要求或异常拒绝，则记录状态并停止继续扩散。

### 7.2 访问频率与礼貌策略

- 默认同一域名并发数：`1`。
- 默认请求间隔：`5-15` 秒随机抖动。
- 对 PDF、公告、静态页面优先采集；动态页面使用更低频率。
- 遇到 `429`、`403`、`503`、验证码页、WAF 提示时立即停止该域名任务，记录状态，不做绕过。
- 支持 `Retry-After` 响应头，严格按服务端建议等待。
- 夜间批处理也必须遵守频率限制，不进行突发请求。

### 7.3 User-Agent 与请求头原则

请求头用于兼容不同站点的正常页面返回，不用于伪装真人、绕过封禁或规避访问限制。

建议配置：

- 项目专用 User-Agent：说明项目名称、用途和联系邮箱，例如 `PolicyCrawler/0.1 (+contact@example.com)`。
- 标准浏览器 User-Agent：仅在页面对普通 HTTP 客户端返回异常时使用。
- `Accept-Language`：根据站点语言设置 `zh-CN,zh;q=0.9` 或 `en-US,en;q=0.9`。
- `Accept`、`Accept-Encoding`、`Connection`：使用常规值。

禁止策略：

- 不轮换大量伪造身份。
- 不绕过验证码。
- 不使用代理池规避封禁。
- 不请求登录态、Cookie 或个人账号数据。
## 8. 技术方案

### 8.1 架构模块

```text
week1-module-Web-Crawler/
  final-result/
    training_samples.jsonl
  pycrawler/
    PRD.md
    README.md
    configs/
      sources.yaml
      categories.yaml
      rate_limits.yaml
    crawler/
      fetcher.py
      parser.py
      pdf_parser.py
      insurance_parser.py
      scheduler.py
      storage.py
      dedupe.py
    data/
      raw/
      text/
      parsed/
      logs/
    tests/
      test_parser.py
      test_dedupe.py
```

### 8.2 推荐技术栈

- Python 3.11+
- `httpx`：同步/异步 HTTP 请求。
- `beautifulsoup4` / `selectolax`：HTML 解析。
- `trafilatura` / `readability-lxml`：正文抽取。
- `pypdf` / `pdfplumber`：PDF 文本解析。
- `playwright`：仅用于普通请求无法渲染的公开页面。
- `sqlite`：本地索引、任务状态、去重和版本管理。
- `jsonlines` / `pandas`：导出 JSONL、CSV。
- `pytest`：单元测试。

### 8.3 采集流程

1. 加载 `sources.yaml` 中的企业、机构、入口 URL、允许主题和限速配置。
2. 抓取政策入口页、服务条款页、帮助中心页、PDF 文档和公告列表。
3. 提取候选链接，只保留政策规则相关 URL。
4. 对候选 URL 去重。
5. 下载 HTML/PDF，保存原始文件。
6. 抽取正文，识别标题、更新时间、正文段落、表格和附件。
7. 根据关键词和规则模型标注政策主题。
8. 生成结构化 JSONL 和 CSV。
9. 输出采集报告：成功、跳过、失败、待人工审核。

### 8.4 Python 代码规范

代码需要长期维护和进入版本管理，因此实现时必须优先保证模块清晰、注释充分、行为可追踪。

- 单个 `.py` 文件建议控制在 `300` 行以内，原则上不超过 `400` 行；超过时需要拆分模块。
- 单个函数建议控制在 `60` 行以内；超过时优先拆成小函数，例如“下载页面”“提取正文”“解析日期”“写入存储”分别处理。
- 每个 `.py` 文件顶部必须写中文模块注释，说明文件意图、负责的边界、输入输出和不负责的事项。
- 每个公开函数必须写中文 docstring，说明函数意图、参数含义、返回值、异常或跳过条件。
- 复杂判断、正则表达式、限速、保险赔付解析、国际术语映射等位置必须写中文注释，解释为什么这样处理。
- 变量名、函数名使用清晰英文，注释和说明使用中文；避免拼音变量名。
- 避免长难句式代码：链式调用、嵌套三元表达式、过长列表推导式应拆成中间变量，并用中文注释说明每一步意图。
- 配置优先放入 `configs/`，不要把公司名单、关键词词表、限速参数硬编码进业务逻辑。
- 禁止把抓取、解析、存储、导出全部堆在一个脚本中；入口脚本只负责调度。
- 对外部站点请求必须通过统一的 `fetcher.py`，确保限速、User-Agent、重试和日志规则不会被绕开。
- 解析失败时返回结构化错误，不直接吞异常；日志需要能定位到来源 URL、公司、主题和失败原因。
- 测试文件与源码模块对应，复杂解析逻辑必须有样例测试，尤其是保价赔付、声明价值、危险品和冷链规则。

## 9. 源站配置初稿

### 9.1 第一批高优先级

| 优先级 | 来源 | 域名 | 目标内容 |
| --- | --- | --- | --- |
| P0 | 中国邮政/EMS | `ems.com.cn`、`chinapost.com.cn` | 邮政寄递、EMS 国内国际、禁限寄、邮寄保险、保价赔付、时效 |
| P0 | 国家邮政局 | `spb.gov.cn` | 监管政策、禁寄目录、快递服务法规 |
| P0 | 顺丰 | `sf-express.com` | 寄件规则、保价、冷运、医药、国际件、危险品 |
| P0 | UPS | `ups.com` | Terms、Service Guide、Dangerous Goods、Customs、Declared Value、Liability |
| P0 | FedEx | `fedex.com` | Service Guide、Dangerous Goods、Lithium Batteries、Customs、Declared Value、Liability |
| P0 | DHL | `dhl.com` | Express Terms、Restricted Commodities、Customs、Shipment Value Protection、Liability |

### 9.2 第二批国内覆盖

| 优先级 | 来源 | 域名 | 目标内容 |
| --- | --- | --- | --- |
| P1 | 京东物流 | `jdl.com`、`jdwl.com` | 服务条款、冷链、大件、保价赔付、禁限寄 |
| P1 | 圆通 | `yto.net.cn` | 禁限寄、服务协议、保价与赔偿规则 |
| P1 | 申通 | `sto.cn` | 禁限寄、服务条款、保价与赔偿规则 |
| P1 | 中通 | `zto.com` | 禁限寄、服务条款、保价与赔偿规则 |
| P1 | 韵达 | `yundaex.com` | 禁限寄、服务条款、保价与赔偿规则 |
| P1 | 极兔 | `jtexpress.cn` | 禁限寄、服务条款、跨境规则 |
| P1 | 德邦 | `deppon.com` | 大件、包装、赔付、禁限寄 |
| P1 | 跨越速运 | `ky-express.com` | 航空件、时效件、禁限寄、赔付 |

### 9.3 第三批国际覆盖

| 优先级 | 来源 | 域名 | 目标内容 |
| --- | --- | --- | --- |
| P2 | USPS | `usps.com` | Postal Explorer、Hazmat、International Mail |
| P2 | Royal Mail | `royalmail.com` | Prohibited and restricted items、international |
| P2 | Japan Post | `post.japanpost.jp` | EMS、international mail、restricted items |
| P2 | Australia Post | `auspost.com.au` | Dangerous goods、international restrictions |
| P2 | Canada Post | `canadapost-postescanada.ca` | Non-mailable matter、customs、liability |
| P2 | Singapore Post | `singpost.com` | International mail、restricted items |
| P2 | UPU | `upu.int` | International postal rules、EMS、standards |
| P2 | IATA | `iata.org` | Dangerous goods、lithium battery guidance |

## 10. 关键词与分类词表

### 10.1 中文关键词

- 禁寄、限寄、禁限寄、禁止寄递、限制寄递、违禁品、禁运品、危险品、危险货物。
- 易燃、易爆、腐蚀、有毒、放射性、磁性、压缩气体、液体、粉末、喷雾、酒精。
- 锂电池、充电宝、带电产品、纯电池、电池设备、航空限制。
- 易碎、玻璃、陶瓷、精密仪器、艺术品、贵重物品、保价、赔付、理赔。
- 邮寄保险、运输保险、足额保价、不足额保价、声明价值、价值证明、赔付上限、免责条款。
- 活体、动物、宠物、植物、种子、土壤、菌种、生物样本、检疫。
- 冷藏、冷冻、冷链、生鲜、医药、疫苗、胰岛素、干冰、温控。
- 海关、清关、报关、申报、商业发票、关税、HS 编码、进出口。

### 10.2 英文关键词

- prohibited items, restricted items, non-mailable, dangerous goods, hazardous materials, hazmat。
- lithium battery, battery-powered equipment, dry ice, flammable, corrosive, toxic, radioactive, magnetized material。
- fragile, declared value, liability, compensation, claim, insurance。
- shipment insurance, value protection, carrier liability, claim deadline, declared value for carriage, declared value for customs。
- live animals, plants, seeds, biological substances, specimens, perishables。
- cold chain, refrigerated, frozen, temperature controlled, healthcare, medical logistics。
- customs, clearance, commercial invoice, duties and taxes, import restrictions, export restrictions。

## 11. 输出成果

### 11.1 数据文件

- `pycrawler/data/parsed/pages.jsonl`：页面级清洗结果。
- `pycrawler/data/parsed/policies.jsonl`：规则级结构化结果。
- `pycrawler/data/parsed/policies.csv`：便于表格查看的结果。
- `pycrawler/data/logs/crawl_report.md`：采集报告。
- `final-result/training_samples.jsonl`：最终保留的训练样本。
### 11.2 报告内容

- 各来源采集数量。
- 按主题统计政策数量。
- 按公司统计覆盖范围。
- 高风险或需人工复核页面列表。
- 最新更新时间不明确的页面列表。
- 解析失败或 PDF 扫描件列表。

## 12. 验收标准

- 至少覆盖 15 家国内快递/物流企业、8 家海外邮政/快递主体、5 类监管/行业来源。
- 每条政策数据必须有原始 URL、标题、来源、抓取时间、主题分类和证据文本。
- 禁限寄、危险品、易碎品、活体、冷链冷冻、国际清关、赔付规则七类主题均有数据。
- 邮寄保险、保价、声明价值、承运商责任限制需要作为独立主题采集和导出。
- 对登录要求、验证码、访问异常的页面必须跳过并记录，不做绕过。
- 输出 JSONL、CSV 和 Markdown 采集报告。
- 核心模块有基础单元测试：URL 去重、正文抽取、主题分类。

## 13. 里程碑

| 阶段 | 目标 | 交付物 |
| --- | --- | --- |
| M1 | 项目初始化与 PRD | `PRD.md`、目录规划、源站清单 |
| M2 | 合规抓取框架 | 限速、请求器、任务队列 |
| M3 | 国内 P0/P1 来源采集 | 中国邮政、EMS、顺丰、国家邮政局、三通一达等 |
| M4 | 国际来源采集 | UPS、FedEx、DHL、USPS、Royal Mail、Japan Post 等 |
| M5 | 特殊品类解析 | 危险品、易碎、活体、冷链、清关、保险保价、赔付分类 |
| M6 | 数据导出与报告 | JSONL、CSV、Markdown 报告、测试结果 |

## 14. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 页面动态渲染 | 普通请求无法提取正文 | 使用 Playwright 低频渲染 |
| 政策更新时间不明确 | 版本追踪困难 | 保存抓取时间、正文哈希，标记 `updated_at_unknown` |
| PDF 扫描件 | 文本抽取失败 | 标记人工复核，不默认 OCR 大规模处理 |
| 多语言术语差异 | 分类不稳定 | 建立中英文词表和人工审核队列 |
| 企业规则变化频繁 | 数据过期 | 使用内容哈希和周期性低频复采检测变化 |
| 特殊品类涉及监管限制 | 误解风险 | 保留原文证据，不做超出原文的结论 |

## 15. 后续代码实现原则

- 先实现合规框架，再扩展站点数量。
- 所有来源通过配置文件管理，不把站点规则硬编码在爬虫主逻辑中。
- 每个域名独立限速、独立失败熔断。
- 抓取、解析、分类、导出分层实现，方便替换解析器。
- 任何异常页面都优先记录和跳过，不做绕过式重试。
- 所有输出保留可追溯证据，便于人工复核。
- 后续新增代码必须遵守“单文件不过长、函数职责单一、中文注释充分”的规范；如果实现变复杂，应优先拆分模块，而不是继续堆叠在同一个文件中。
