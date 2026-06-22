# Data Format

## 1. 数据目录

当前数据目录：

```text
/Users/bizi/Desktop/邮政实习/week2/data/
├── README.md
├── CSDS/
│   ├── train.json
│   ├── val.json
│   ├── test.json
│   ├── ._train.json
│   ├── ._val.json
│   └── ._test.json
├── llm_filter/
│   └── postal_filter_results.json
└── embeddings/
    ├── dialogue_embeddings.h5
    └── dialogue_metadata.json
```

注意：

- `CSDS/._train.json`、`CSDS/._val.json`、`CSDS/._test.json` 是 macOS AppleDouble 文件。
- 导入程序必须跳过 `._*.json`。
- 真正参与处理的数据文件只有 `train.json`、`val.json`、`test.json`。

## 2. CSDS 原始数据格式

文件：

- `/Users/bizi/Desktop/邮政实习/week2/data/CSDS/train.json`
- `/Users/bizi/Desktop/邮政实习/week2/data/CSDS/val.json`
- `/Users/bizi/Desktop/邮政实习/week2/data/CSDS/test.json`

整体格式：

- JSON array。
- 每个元素是一条对话。

数量：

- `train.json`：9101 条。
- `val.json`：800 条。
- `test.json`：800 条。

每条对话字段固定为：

```text
DialogueID
QRole
QA
Session_id
Dialogue
UserSumm
AgentSumm
FinalSumm
```

### 2.1 对话主字段

示意结构：

```json
{
  "DialogueID": 3559,
  "QRole": "用户",
  "QA": [],
  "Session_id": "13f09c952fc34164e4e511074c74bcd3",
  "Dialogue": [],
  "UserSumm": "...",
  "AgentSumm": "...",
  "FinalSumm": "..."
}
```

字段说明：

- `DialogueID`：原始对话 ID，整数。
- `Session_id`：原始会话 ID，字符串。
- `QRole`：提问角色，当前样例中为“用户”。
- `Dialogue`：完整多轮对话。
- `QA`：对话中抽取出的问答摘要和 intent。
- `UserSumm`：用户侧总结。
- `AgentSumm`：客服侧总结。
- `FinalSumm`：整段对话总结。

### 2.2 Dialogue 格式

`Dialogue` 是 array，每个元素字段固定为：

```text
speaker
turn
utterance
```

示意：

```json
{
  "speaker": "Q",
  "turn": 2,
  "utterance": "地址 写错 了"
}
```

字段说明：

- `speaker`：说话人。
  - `Q` 表示用户。
  - `A` 表示客服。
- `turn`：轮次编号，整数。
- `utterance`：原始发言文本。

实现要求：

- RAG 引用展示时优先展示 `Dialogue` 中的原始多轮文本。
- 保存引用时需要保留 `turn` 和 `speaker`，方便前端展示“用户/客服”来源。

### 2.3 QA 格式

`QA` 是 array，每个元素字段固定为：

```text
QueSumm
AnsSummShort
AnsSummLong
QueSummUttIDs
AnsSummShortUttIDs
AnsSummLongUttIDs
QASumm
intent
```

示意：

```json
{
  "QueSumm": "用户询问地址写错怎么处理。",
  "AnsSummShort": "客服回答客户提供咨询订单，在确认后发现商品暂未付款，客户修改地址即可。",
  "AnsSummLong": "客服回答客户提供咨询订单，在确认后发现商品暂未付款，客户修改地址即可。",
  "QueSummUttIDs": [2],
  "AnsSummShortUttIDs": [3, 6, 7],
  "AnsSummLongUttIDs": [3, 6, 7],
  "QASumm": "用户询问地址写错怎么处理。客服回答客户提供咨询订单，在确认后发现商品暂未付款，客户修改地址即可。",
  "intent": "修改订单"
}
```

字段说明：

- `QueSumm`：用户问题摘要。
- `AnsSummShort`：客服短回答摘要。
- `AnsSummLong`：客服长回答摘要。
- `QueSummUttIDs`：用户问题对应的 `Dialogue.turn` 列表。
- `AnsSummShortUttIDs`：短回答对应的 `Dialogue.turn` 列表。
- `AnsSummLongUttIDs`：长回答对应的 `Dialogue.turn` 列表。
- `QASumm`：问答合并摘要。
- `intent`：业务意图。

实现要求：

- 向量入库文本可以优先使用 `QASumm` + 对应原始 turn 文本。
- 引用展示不能只展示摘要，必须能回到 `Dialogue` 原文。
- `intent` 可以存入 metadata，用于工单的 `issue_type` 候选。

## 3. llm_filter 格式

文件：

- `/Users/bizi/Desktop/邮政实习/week2/data/llm_filter/postal_filter_results.json`

整体格式：

- JSON object。
- 顶层 key 固定为 `train`、`val`、`test`。
- 每个 split 对应一个 array。

数量和邮政相关统计：

| split | 总数 | 邮政相关 true | 非邮政 false |
| --- | ---: | ---: | ---: |
| train | 9101 | 5376 | 3725 |
| val | 800 | 459 | 341 |
| test | 800 | 486 | 314 |

每条筛选记录字段固定为：

```text
index
session_id
dialogue_id
is_postal_related
raw_response
```

示意：

```json
{
  "index": 0,
  "session_id": "13f09c952fc34164e4e511074c74bcd3",
  "dialogue_id": 3559,
  "is_postal_related": true,
  "raw_response": "true"
}
```

字段说明：

- `index`：对应 CSDS split array 的下标。
- `session_id`：对应 CSDS 的 `Session_id`。
- `dialogue_id`：对应 CSDS 的 `DialogueID`。
- `is_postal_related`：是否邮政相关。
- `raw_response`：筛选模型原始输出，当前为字符串 `"true"` 或 `"false"`。

实现要求：

- 只允许 `is_postal_related == true` 的数据进入 pgvector。
- 不要用 `raw_response` 作为主要判断字段，只作为审计字段保存。
- 必须用 `split + index + session_id + dialogue_id` 四个信息校验映射。
- 如果 `index` 对应不上，或 `session_id/dialogue_id` 不一致，必须跳过并记录错误。

## 4. embeddings 元数据格式

文件：

- `/Users/bizi/Desktop/邮政实习/week2/data/embeddings/dialogue_metadata.json`

整体格式：

- JSON object。
- 顶层 key 固定为 `train`、`val`、`test`。
- 每个 split 对应一个 array。

每条 metadata 字段固定为：

```text
index
session_id
dialogue_id
turn_count
```

示意：

```json
{
  "index": 0,
  "session_id": "13f09c952fc34164e4e511074c74bcd3",
  "dialogue_id": 3559,
  "turn_count": 23
}
```

字段说明：

- `index`：对应 CSDS split array 的下标。
- `session_id`：对应 CSDS 的 `Session_id`。
- `dialogue_id`：对应 CSDS 的 `DialogueID`。
- `turn_count`：对应 `Dialogue` 的轮次数。

实现要求：

- metadata 可以用于核对旧 embedding 与 CSDS 的对齐关系。
- 新系统以 `qwen3-embedding:8b` 重新生成并写入 pgvector 为准。
- 如果复用旧 embedding，必须确认旧模型来源和向量维度，否则不要直接混用。

## 5. H5 embedding 文件格式

文件：

- `/Users/bizi/Desktop/邮政实习/week2/data/embeddings/dialogue_embeddings.h5`

H5 dataset：

| dataset | shape | dtype |
| --- | --- | --- |
| `train` | `(9101, 4096)` | `float32` |
| `val` | `(800, 4096)` | `float32` |
| `test` | `(800, 4096)` | `float32` |

对齐关系：

- `dialogue_embeddings.h5["train"][i]`
  对应 `dialogue_metadata.json["train"][i]`
  也对应 `CSDS/train.json[i]`
  和 `postal_filter_results.json["train"][i]`。
- `val`、`test` 同理。

实现要求：

- 旧 H5 embedding 只作为参考或迁移输入。
- 如果导入旧 H5，必须同时读取 `dialogue_metadata.json` 校验身份。
- 如果直接重新 embedding，则不依赖旧 H5。

## 6. 三类数据的主对齐规则

对每个 split：

```text
CSDS/{split}.json[index]
postal_filter_results.json[split][index]
dialogue_metadata.json[split][index]
dialogue_embeddings.h5[split][index]
```

必须满足：

```text
CSDS item Session_id == filter session_id == metadata session_id
CSDS item DialogueID == filter dialogue_id == metadata dialogue_id
filter index == metadata index == CSDS array index
```

只有上述条件都满足，且 `is_postal_related == true`，才允许入库。

## 7. 入库建议文本

每条邮政相关对话生成一个 `PostalDocument`。

建议 `content` 组成：

```text
会话ID: {Session_id}
对话ID: {DialogueID}
业务意图: {QA.intent 列表}
问答摘要:
{QA.QASumm 列表}
原始对话:
用户: ...
客服: ...
```

metadata 建议保存：

```json
{
  "split": "train",
  "index": 0,
  "session_id": "...",
  "dialogue_id": 3559,
  "turn_count": 23,
  "intents": ["修改订单", "优惠券退回"],
  "source_path": "/Users/bizi/Desktop/邮政实习/week2/data/CSDS/train.json"
}
```

## 8. 实现风险

- 不能遍历 `CSDS/*.json` 时把 `._*.json` 当成数据。
- 不能只根据 `index` 入库，必须同时校验 `session_id` 和 `dialogue_id`。
- 不能把 `is_postal_related == false` 的客服泛化数据放入 pgvector。
- 不能把旧 H5 embedding 和新 `qwen3-embedding:8b` embedding 混在同一个向量字段里。
- 不能只保存摘要不保存原始对话，否则引用展示无法解释来源。
