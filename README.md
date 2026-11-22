# 奖池分账（AI Agent 全栈开发笔试题）

## 1. 会出错的输入样例

原代码中，`split_pool` 对每个用户分别执行浮点乘法除法后直接 `round(...)` 四舍五入，导致整体总和经常不守恒。

### 代表性出错输入（三个数）

- **输入**：`pool_cents = 10000`，`weights = [1, 1, 1]`（即原代码 `__main__` 示例本身）
  - 实际输出：`[3333, 3333, 3333]`
- **实际的和**：`9999`
- **应有的和**：`10000`（少发了 `1` 分）

### 其他典型出错场景

| 场景 | 输入 (`pool_cents, weights`) | 原代码实际输出 | 实际的和 | 应有的和 | 误差原因 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| 多发（向上舍入叠加） | `2, [1, 1, 1]` | `[1, 1, 1]` | `3` | `2` | `2/3 ≈ 0.667`，三人均被 `round` 成 `1` |
| Python 银行家舍入（偶舍奇入） | `10, [1, 1, 1, 1]` | `[2, 2, 2, 2]` | `8` | `10` | `2.5` 在 Python `round()` 中向偶数 `2` 舍入，少发 `2` 分 |
| 超大整数浮点精度丢失 | `10**18 + 1, [1, 1, 1]` | `[333333333333333312, ...]` | `999999999999999936` | `1000000000000000001` | IEEE-754 `float64` 仅 53 位尾数精度，超过 $2^{53}$ 发生截断 |

---

## 2. 修改方案说明

将 [pool_split.py](pool_split.py) 中的浮点逐项四舍五入，替换为**纯整数最大余额法（Largest Remainder Method / Hamilton Method）**，并补充边界校验：

1. **类型与非负校验**：通过 `_validate_non_negative_int` 显式拒绝 `bool`（Python 中 `bool` 是 `int` 子类）、浮点数及负数；当 `pool_cents > 0` 但 `weights` 为空或总权重为 `0` 时抛出 `ValueError`（无法满足总额守恒）；当 `pool_cents == 0` 时返回全 `0` 列表。
2. **纯整数向下取整与精确余数**：对每个权重 `w` 计算 `base, rem = divmod(pool_cents * w, total)`。其中 `base` 为理论配额的整数部分，`rem` 为精确余数分子（所有分母同为 `total`，可直接比较大小，彻底消除浮点精度损失）。
3. **余数重分配**：计算待分配差额 `leftover = pool_cents - sum(bases)`，按 `(-rem, -weight, index)` 排序，给前 `leftover` 名用户每人加 `1` 分。

### 核心性质证明

- **严格总额守恒**：由于 $pool\_cents \cdot w = base_i \cdot total + rem_i$，对所有 $i$ 求和得 $pool\_cents \cdot total = total \cdot \sum base_i + \sum rem_i$，故 $leftover = \frac{\sum rem_i}{total}$ 为非负整数。又因每项 $0 \le rem_i < total$，且只有 $rem_i > 0$ 的项才会贡献到分子中，因此 $0 \le leftover < |\{i : rem_i > 0\}|$，前 `leftover` 个位置必定对应正余数，从而：
  - 总和严格等于 `pool_cents`；
  - 权重为 `0` 的用户余数必为 `0`，绝不会被分到多余的 `1` 分。
- **配额规则（Quota Rule）**：每人最终分得 $a_i \in \{base_i, base_i + 1\}$，因此与理想连续值 $q_i = \frac{pool\_cents \cdot w_i}{total}$ 的误差严格满足 $|a_i - q_i| < 1$ 分。

---

## 3. 测试与两次运行输出

测试文件为 [test_pool_split.py](test_pool_split.py)，仅依赖 Python 标准库（`unittest`、`random`、`itertools`），无需第三方依赖，运行命令：

```bash
python -B -m unittest -v test_pool_split.py
```

### 3.1 在未修改的 `pool_split.py` 上运行（预期失败）

```text
test_bankers_rounding_loss (test_pool_split.TestSplitPool.test_bankers_rounding_loss) ... FAIL
test_exact_tie_breaking_and_largest_remainder (test_pool_split.TestSplitPool.test_exact_tie_breaking_and_largest_remainder) ... FAIL
test_exhaustive_small_space (test_pool_split.TestSplitPool.test_exhaustive_small_space) ... FAIL
test_input_list_not_mutated (test_pool_split.TestSplitPool.test_input_list_not_mutated) ... ok
test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) ... 
  test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[]) ... FAIL
  test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[0, 0, 0]) ... ERROR
  test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=-1, weights=[1, 2]) ... FAIL
  test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[1, -1, 2]) ... FAIL
  test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100.0, weights=[1, 2]) ... FAIL
  test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=True, weights=[1, 2]) ... FAIL
  test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[1, 2.5]) ... FAIL
  test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[1, False]) ... FAIL
test_large_integer_no_float_precision_loss (test_pool_split.TestSplitPool.test_large_integer_no_float_precision_loss) ... FAIL
test_many_small_weights (test_pool_split.TestSplitPool.test_many_small_weights) ... FAIL
test_overpay_equal_three (test_pool_split.TestSplitPool.test_overpay_equal_three) ... FAIL
test_property_based_random_fuzz (test_pool_split.TestSplitPool.test_property_based_random_fuzz) ... FAIL
test_single_user (test_pool_split.TestSplitPool.test_single_user) ... ok
test_underpay_equal_three (test_pool_split.TestSplitPool.test_underpay_equal_three) ... FAIL
test_zero_pool (test_pool_split.TestSplitPool.test_zero_pool) ... ERROR
test_zero_weights_mixed (test_pool_split.TestSplitPool.test_zero_weights_mixed) ... FAIL

======================================================================
ERROR: test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[0, 0, 0])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 112, in test_invalid_inputs
    split_pool(pool_cents, weights)
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\pool_split.py", line 27, in split_pool
    return [round(pool_cents * w / total) for w in weights]
                  ~~~~~~~~~~~~~~~^~~~~~~
ZeroDivisionError: division by zero

======================================================================
ERROR: test_zero_pool (test_pool_split.TestSplitPool.test_zero_pool)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 91, in test_zero_pool
    self.assertEqual(split_pool(0, [0, 0]), [0, 0])
                     ^^^^^^^^^^^^^^^^^^^^^
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\pool_split.py", line 27, in split_pool
    return [round(pool_cents * w / total) for w in weights]
                  ~~~~~~~~~~~~~~~^~~~~~~
ZeroDivisionError: division by zero

======================================================================
FAIL: test_bankers_rounding_loss (test_pool_split.TestSplitPool.test_bankers_rounding_loss)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 60, in test_bankers_rounding_loss
    self._assert_invariants(10, [1, 1, 1, 1], result)
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 23, in _assert_invariants
    self.assertEqual(sum(result), pool_cents)
AssertionError: 8 != 10

======================================================================
FAIL: test_exact_tie_breaking_and_largest_remainder (test_pool_split.TestSplitPool.test_exact_tie_breaking_and_largest_remainder)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 77, in test_exact_tie_breaking_and_largest_remainder
    self.assertEqual(split_pool(10000, [1, 1, 1]), [3334, 3333, 3333])
AssertionError: Lists differ: [3333, 3333, 3333] != [3334, 3333, 3333]

First differing element 0:
3333
3334

- [3333, 3333, 3333]
+ [3334, 3333, 3333]

======================================================================
FAIL: test_exhaustive_small_space (test_pool_split.TestSplitPool.test_exhaustive_small_space)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 134, in test_exhaustive_small_space
    self._assert_invariants(pool_cents, weights, result)
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 23, in _assert_invariants
    self.assertEqual(sum(result), pool_cents)
AssertionError: 0 != 1

======================================================================
FAIL: test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 111, in test_invalid_inputs
    with self.assertRaises(ValueError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ValueError not raised

======================================================================
FAIL: test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=-1, weights=[1, 2])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 111, in test_invalid_inputs
    with self.assertRaises(ValueError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ValueError not raised

======================================================================
FAIL: test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[1, -1, 2])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 111, in test_invalid_inputs
    with self.assertRaises(ValueError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ValueError not raised

======================================================================
FAIL: test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100.0, weights=[1, 2])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 121, in test_invalid_inputs
    with self.assertRaises(TypeError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: TypeError not raised

======================================================================
FAIL: test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=True, weights=[1, 2])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 121, in test_invalid_inputs
    with self.assertRaises(TypeError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: TypeError not raised

======================================================================
FAIL: test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[1, 2.5])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 121, in test_invalid_inputs
    with self.assertRaises(TypeError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: TypeError not raised

======================================================================
FAIL: test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) (pool_cents=100, weights=[1, False])
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 121, in test_invalid_inputs
    with self.assertRaises(TypeError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: TypeError not raised

======================================================================
FAIL: test_large_integer_no_float_precision_loss (test_pool_split.TestSplitPool.test_large_integer_no_float_precision_loss)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 74, in test_large_integer_no_float_precision_loss
    self._assert_invariants(pool_cents, weights, result)
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 23, in _assert_invariants
    self.assertEqual(sum(result), pool_cents)
AssertionError: 999999999999999936 != 1000000000000000001

======================================================================
FAIL: test_many_small_weights (test_pool_split.TestSplitPool.test_many_small_weights)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 65, in test_many_small_weights
    self._assert_invariants(pool_cents, weights, result)
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 23, in _assert_invariants
    self.assertEqual(sum(result), pool_cents)
AssertionError: 0 != 1

======================================================================
FAIL: test_overpay_equal_three (test_pool_split.TestSplitPool.test_overpay_equal_three)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 56, in test_overpay_equal_three
    self._assert_invariants(2, [1, 1, 1], result)
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 23, in _assert_invariants
    self.assertEqual(sum(result), pool_cents)
AssertionError: 3 != 2

======================================================================
FAIL: test_property_based_random_fuzz (test_pool_split.TestSplitPool.test_property_based_random_fuzz)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 161, in test_property_based_random_fuzz
    self._assert_invariants(pool_cents, weights, result)
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 23, in _assert_invariants
    self.assertEqual(sum(result), pool_cents)
AssertionError: 30 != 32

======================================================================
FAIL: test_underpay_equal_three (test_pool_split.TestSplitPool.test_underpay_equal_three)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 52, in test_underpay_equal_three
    self._assert_invariants(10000, [1, 1, 1], result)
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 23, in _assert_invariants
    self.assertEqual(sum(result), pool_cents)
AssertionError: 9999 != 10000

======================================================================
FAIL: test_zero_weights_mixed (test_pool_split.TestSplitPool.test_zero_weights_mixed)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 85, in test_zero_weights_mixed
    self._assert_invariants(10, weights, result)
  File "D:\Documents\刘健锋-个人简历\五维数据\submission\test_pool_split.py", line 23, in _assert_invariants
    self.assertEqual(sum(result), pool_cents)
AssertionError: 9 != 10

----------------------------------------------------------------------
Ran 13 tests in 0.008s

FAILED (failures=16, errors=2)
```

### 3.2 在修改后的 `pool_split.py` 上运行（全部通过）

```text
test_bankers_rounding_loss (test_pool_split.TestSplitPool.test_bankers_rounding_loss) ... ok
test_exact_tie_breaking_and_largest_remainder (test_pool_split.TestSplitPool.test_exact_tie_breaking_and_largest_remainder) ... ok
test_exhaustive_small_space (test_pool_split.TestSplitPool.test_exhaustive_small_space) ... ok
test_input_list_not_mutated (test_pool_split.TestSplitPool.test_input_list_not_mutated) ... ok
test_invalid_inputs (test_pool_split.TestSplitPool.test_invalid_inputs) ... ok
test_large_integer_no_float_precision_loss (test_pool_split.TestSplitPool.test_large_integer_no_float_precision_loss) ... ok
test_many_small_weights (test_pool_split.TestSplitPool.test_many_small_weights) ... ok
test_overpay_equal_three (test_pool_split.TestSplitPool.test_overpay_equal_three) ... ok
test_property_based_random_fuzz (test_pool_split.TestSplitPool.test_property_based_random_fuzz) ... ok
test_single_user (test_pool_split.TestSplitPool.test_single_user) ... ok
test_underpay_equal_three (test_pool_split.TestSplitPool.test_underpay_equal_three) ... ok
test_zero_pool (test_pool_split.TestSplitPool.test_zero_pool) ... ok
test_zero_weights_mixed (test_pool_split.TestSplitPool.test_zero_weights_mixed) ... ok

----------------------------------------------------------------------
Ran 13 tests in 0.193s

OK
```

---

## 4. AI 使用情况说明

本次完成题目过程中使用了 AI 编程助手（Antigravity）辅助分析与代码/测试编写：

1. **提出的问题**：
   - 分析原 `split_pool` 为何无法保证总和守恒，除了多发/少发外还有哪些边界风险（如 `round` 银行家舍入、除零、大数浮点截断等）。
   - 如何设计严格守恒、无浮点误差、且满足配额公平性的分账算法与属性测试。
2. **得到的回答**：
   - AI 指出了原代码依赖 `float` 除法与逐项 `round()` 导致舍入误差无法抵消，以及超过 $2^{53}$ 的整数会发生 IEEE-754 精度截断等问题。
   - 给出了基于纯整数 `divmod` 的**最大余额法（Hamilton Method）**实现思路，以及使用不变量（守恒、配额规则、非负、单调性）进行穷举和随机模糊测试的验证框架。
3. **是否直接采用（人工审查与调整）**：
   - **未直接照搬**，而是逐行审阅并做了以下几项关键把控与调整：
     - **保持函数签名兼容**：保留 `split_pool(pool_cents: int, weights: list[int]) -> list[int]` 原接口，未擅自新增参数破坏既有调用约定。
     - **明确零池/空池语义**：约定 `pool_cents == 0` 时返回全 `0`（或空列表），而 `pool_cents > 0` 且 `weights` 为空或总和为 `0` 时显式抛出 `ValueError`（因为此时数学上不可能满足总和守恒）。
     - **防御 Python `bool` 隐式转 `int`**：Python 中 `isinstance(True, int)` 为 `True`，人工确认增加了 `isinstance(value, bool)` 检查并抛出 `TypeError`。
     - **确定性平局规则权衡**：当余数相同时采用 `(-remainders[i], -weights[i], i)`，保证同等输入下结果完全确定且对大贡献者略微倾斜；同时在文档中明确线上可结合日期做哈希轮换避免索引偏置。
     - **零第三方依赖测试**：确认目标环境未安装 `pytest` / `hypothesis`，将属性测试与穷举测试改写为纯标准库 `unittest` + 固定种子 `random.Random`，确保开箱即运行。
4. **如何确认其正确**：
   - **数学推导确认**：严格证明了 `divmod` 下 $0 \le leftover < |\{i : rem_i > 0\}|$ 与配额不等式 $|a_i - q_i| < 1$，从原理上保证无任意反例。
   - **红绿测试对比**：先在未修改的 `pool_split.py` 上运行 `test_pool_split.py`，确认覆盖核心 bug 与边界异常的用例均失败（`FAILED (failures=16, errors=2)`）；再替换为修改后代码复测，确认全部 13 个测试方法通过（`OK`）。
   - **大规模不变量覆盖**：通过 `test_exhaustive_small_space`（覆盖 2,604 组确定性小规模组合）和 `test_property_based_random_fuzz`（覆盖 2,000 组含超大整数、极端偏态、稀疏零权重的随机组合）用纯整数不等式逐一校验所有不变量。

---

## 5. 补充思考（对应题目可选部分）

### Q1：测试覆盖了多少组输入？有没有比手写样例更不容易漏掉问题的写法？

- **覆盖数量**：除 11 个针对特定场景的单元测试外，`test_exhaustive_small_space` 穷举了 $pool\_cents \in [0, 20]$ 与长度 $1\sim 3$、单权重 $0\sim 4$ 的全部 **2,604** 组有效输入；`test_property_based_random_fuzz` 额外随机生成了 **2,000** 组（人数 $1\sim 100$，含微小池、常规池、$10^{16}\sim 10^{18}$ 超大池、等权重与稀疏零权重）测试案例，合计超过 **4,600 组**输入。
- **更好的写法**：**基于性质的测试（Property-Based Testing）**（如工程中常用的 `Hypothesis` 库）。与手写枚举预期输出不同，只需声明任意合法输入都必须满足的不变量（总额守恒、非负、0 权重得 0、配额误差 $< 1$ 分、单调性），由测试框架自动探索边界并做最小反例缩减（shrinking），最不容易漏掉隐蔽的边界组合。

### Q2：修改后，多出或缺少的那几分钱分配给了谁？依据是什么？换一个人是否可行？

- **分配给了谁、依据是什么**：采用**最大余额法（Hamilton Method）**。先按 `pool_cents * w // total` 给每个人发整数基础分，剩余的 `leftover` 分钱（总人数以内）按**小数余数（精确余数分子 `rem`）从大到小**，每人补 `1` 分。这在数学上保证了每个人的分配误差严格小于 `1` 分，且离精确比例最近的人优先拿到这 `1` 分。
- **余数相同时的策略与换人可行性**：
  - 当前在无额外业务字段的情况下，按 `(-rem, -weight, index)` 打破平局（即余数相同先给贡献权重更大者，再按列表索引靠前者），优点是纯函数、完全确定且可复现。
  - **换一个人是可行的**，但建议在**不破坏配额规则**的前提下换人。例如：如果直接把余数全部塞给「最后一个人」或「权重最大的人」，当有多个用户余数同为 0.9 分而差额为 5 分时，直接塞给某一人会导致其多拿 5 分，破坏公平性。
  - **线上生产实践建议**：由于当前实现中当权重全相同且除不尽时，靠前索引（如 `index=0`）会固定多拿 1 分，长期运行会产生系统性偏置。在线上完整业务中，建议将平局键替换为基于**日期与用户 ID 的确定性哈希**（如 `sha256(f"{date}:{user_id}")`），既能在单日保持幂等可重放，又能在跨天尺度上让余数红利均匀落到每位用户头上。

### Q3：这段代码是否还有其他会出错的输入？

除正整数常规比例分账外，原代码还存在以下出错输入（均已在本次修改与测试中处理/覆盖）：
1. **`weights` 为空列表 `[]` 或全 `0`（如 `[0, 0, 0]`）**：原代码会直接触发 `ZeroDivisionError: division by zero`；修改后若 `pool_cents > 0` 则显式抛出 `ValueError`，若 `pool_cents == 0` 则安全返回 `[]` 或全 `0` 列表。
2. **超大整数（$pool\_cents \cdot w > 2^{53}$）**：原代码使用浮点除法，`float64` 精度丢失导致即便能整除也会分错总额（如 `split_pool(10**18 + 1, [1, 1, 1])` 实际和为 `999999999999999936`）；修改后全流程纯整数计算，支持 Python 任意精度大整数。
3. **负数金额或负权重**：原代码会算出负金额且无任何报错；修改后显式抛出 `ValueError`。
4. **非整数或 `bool` 类型（如 `100.0`、`True`、`False`）**：原代码会静默将 `True/False` 当作 `1/0` 参与运算或返回浮点相关异常结果；修改后显式抛出 `TypeError`。
