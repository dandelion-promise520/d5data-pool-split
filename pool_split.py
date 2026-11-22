"""
pool_split.py —— 每日瓜分奖池的分账逻辑

这是我们线上「每日瓜分奖池」的真实代码，为这道题做了简化
（去掉了数据库读写和日期处理，只留下算钱的部分）。

背景：
  平台每天放一个奖池。当天达标的用户，按各自的贡献权重瓜分池子里的钱。

约定：
  · 所有金额都是整数「分」，系统里不存在半分钱。
  · weights 是每个人的贡献权重（线上用的是「合格采集秒数」）。

硬规则（产品定的，不能破）：
  分完之后，所有人拿到的钱加起来必须【正好等于】池子总额。
  多一分 = 平台凭空多发了钱。
  少一分 = 有人的钱卡在系统里没发出去。
"""


def _validate_non_negative_int(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be a non-bool int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def split_pool(pool_cents: int, weights: list[int]) -> list[int]:
    """把 pool_cents 按 weights 的比例分给每个人，返回每人拿到多少分。

    使用纯整数最大余额法（Largest Remainder Method / Hamilton Method）：
    1. 先用整数除法计算每人应得的基础份额与精确余数分子；
    2. 再将差额 leftover（0 <= leftover < 有效参与人数）按余数从大到小每人补 1 分；
    3. 余数相同时按权重降序、索引升序打破平局，保证确定性与无浮点精度丢失。

    返回列表与 weights 一一对应。
    """
    _validate_non_negative_int(pool_cents, "pool_cents")
    for idx, w in enumerate(weights):
        _validate_non_negative_int(w, f"weights[{idx}]")

    if not weights:
        if pool_cents == 0:
            return []
        raise ValueError("weights cannot be empty when pool_cents > 0")

    total = sum(weights)
    if total == 0:
        if pool_cents == 0:
            return [0] * len(weights)
        raise ValueError("sum(weights) must be positive when pool_cents > 0")

    if pool_cents == 0:
        return [0] * len(weights)

    bases: list[int] = []
    remainders: list[int] = []
    for w in weights:
        base, rem = divmod(pool_cents * w, total)
        bases.append(base)
        remainders.append(rem)

    leftover = pool_cents - sum(bases)
    if leftover > 0:
        order = sorted(
            range(len(weights)),
            key=lambda i: (-remainders[i], -weights[i], i),
        )
        for idx in order[:leftover]:
            bases[idx] += 1

    return bases


if __name__ == "__main__":
    # 奖池 100 元，三个人权重相同：总和严格等于 10000 分
    res = split_pool(10000, [1, 1, 1])
    print(res, "sum =", sum(res))
