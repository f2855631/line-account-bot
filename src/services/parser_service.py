import re
import ast
import operator
from datetime import datetime

# --- 安全計算器：只允許數字與四則運算，無法執行任何函式或屬性存取 ---

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,   # 負號，例如 -100
    ast.UAdd: operator.pos,   # 正號，例如 +100
}

def _safe_eval(node):
    """
    遞迴走訪 AST 節點，只允許數字常量與四則運算。
    任何其他語法（函式呼叫、屬性存取、變數等）都會直接 raise ValueError。
    """
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)

    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"不允許的常量類型: {type(node.value)}")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"不允許的運算符: {op_type}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        # 防止除以零
        if op_type == ast.Div and right == 0:
            raise ValueError("除以零")
        return _ALLOWED_OPERATORS[op_type](left, right)

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_OPERATORS:
            raise ValueError(f"不允許的一元運算符: {op_type}")
        return _ALLOWED_OPERATORS[op_type](_safe_eval(node.operand))

    else:
        raise ValueError(f"不允許的語法節點: {type(node)}")


def safe_calculate(formula_str: str) -> float:
    """
    安全地計算四則運算算式字串，回傳 float。
    若格式錯誤或包含非法語法則 raise ValueError。
    """
    if not formula_str or not formula_str.strip():
        raise ValueError("算式為空")

    # 全型符號正規化
    clean = (formula_str
             .replace('＋', '+')
             .replace('－', '-')
             .replace('×', '*')
             .replace('÷', '/'))

    # 只保留合法字元（數字、小數點、四則運算符、括號、空白）
    clean = re.sub(r'[^0-9+\-*/().\s]', '', clean).strip()

    if not clean:
        raise ValueError("清洗後算式為空")

    tree = ast.parse(clean, mode='eval')
    return _safe_eval(tree)


# --- 主解析函式（介面不變，只換掉計算核心）---

def parse_accounting_content(user_msg):
    lines = [l.strip() for l in user_msg.split('\n') if l.strip()]
    results = []

    for line in lines:
        pattern = r'^(?:(\d{4}/\d{1,2}/\d{1,2})\s+)?([^0-9+\-*/().\s：:]+)[\s：:]*([+-]?\d[0-9+\-*/().\s]*)(?:\s+(.*))?$'
        match = re.match(pattern, line)

        if match:
            date_part, target_name, formula, item = match.groups()

            # --- 處理日期 ---
            if date_part:
                try:
                    dt = datetime.strptime(date_part, '%Y/%m/%d')
                    final_date = dt.strftime('%Y-%m-%d')
                except Exception:
                    final_date = datetime.now().strftime('%Y-%m-%d')
            else:
                final_date = datetime.now().strftime('%Y-%m-%d')

            target_name = target_name.strip()
            item_name = item.strip() if item and item.strip() else None

            try:
                val = safe_calculate(formula)
                diff = int(round(val))

                results.append({
                    "date": final_date,
                    "name": target_name,
                    "amount": diff,
                    "item": item_name
                })
            except Exception as e:
                print(f"⚠️ 解析單行算式失敗 ({line}): {e}")
                continue

    return results