from typing import TypedDict, Optional


class FinanceState(TypedDict, total=False):

    # 输入
    input_file: str
    thread_id: str

    # 中间结果
    document: dict
    metrics: dict
    risk: dict
    browser_result: dict

    # 最终输出
    report: dict