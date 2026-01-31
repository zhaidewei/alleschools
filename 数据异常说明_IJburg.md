# IJburg College (100, 100) 数据异常说明

## 结论：**不是计算错误，是原始数据样本极少**

### 1. 在 `schools_xy_coords.csv` 中

- **28DH01** IJburg College, AMSTERDAM, HAVO/VWO → X_linear=100, Y_linear=100

### 2. 在 `duo_examen_raw_all.csv` 中

- **28DH01 只有一行**：`"28DH";"28DH01";"IJburg College";"AMSTERDAM";"VWO";"61";"VWO - N&G";...`
- 即：该校在 DUO 数据里**只出现了一个组合**——**VWO + 专业 N&G**（理科）。
- 各年考生数列（EXAMENKANDIDATEN TOTAAL）多为 `"<5"`（隐私处理后按 2 计），即每年只有极少考生。

### 3. 计算逻辑（`calc_xy_coords.py`）

- X = VWO 人数 / (HAVO+VWO) 总人数 → 只有 VWO 一行 ⇒ **100%**
- Y = 理科人数 / (HAVO+VWO) 总人数 → 只有 N&G ⇒ **100%**

所以 (100, 100) 是**在“仅一条 VWO-N&G 记录且人数极少”的前提下的正确结果**，并非算错。

### 4. 处理方式

- 在 `calc_xy_coords.py` 中增加 **最小样本量过滤**：`MIN_HAVO_VWO_TOTAL = 20`。
- 若某校 HAVO+VWO 总考生数（5 年合计）**低于 20**，则**不写入** `schools_xy_coords.csv`，避免此类极端点。
- 重新运行 `python3 calc_xy_coords.py` 后，IJburg College 将不再出现在坐标 CSV 中；若需保留但做标记，可再改为“输出但加 flag”。
