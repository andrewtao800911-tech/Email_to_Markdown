#!/usr/bin/env python3
"""
邮件去重处理 - 文本处理和匹配工具
整合03目录中的utils.py功能
"""

import re
import unicodedata
from difflib import SequenceMatcher

# 可选的分词器
try:
    import jieba
except Exception:
    jieba = None

try:
    from tinysegmenter import TinySegmenter
    tinysegmenter = TinySegmenter()
except Exception:
    tinysegmenter = None

# 正则表达式定义
RE_QUOTE = re.compile(r'^\s*>+\s?', re.MULTILINE)
RE_REPLY_HEADER = re.compile(r'(^On\s.+wrote:)|(^From:\s.+\n)|(^发件人：)|(^-----Original Message-----)', re.IGNORECASE | re.MULTILINE)
RE_SIGNATURE_DELIM = re.compile(r'(--|__|==)\s*$', re.MULTILINE)
RE_HTML_TAG = re.compile(r'<[^>]+>')
RE_NON_ALNUM = re.compile(r'[^0-9A-Za-z\u4e00-\u9fff\u3000-\u303f\u3040-\u30ff]')
CJK_RE = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff]')
RE_FORWARD_BLOCK = re.compile(r'(From:\s.*\nTo:\s.*\nSubject:)', re.IGNORECASE)
RE_WHITESPACE = re.compile(r'\s+')

def normalize_whitespace(s: str) -> str:
    """标准化空白字符"""
    return RE_WHITESPACE.sub(' ', s).strip()

def strip_html(s: str) -> str:
    """去除HTML标签"""
    return RE_HTML_TAG.sub(' ', s)

def remove_reply_headers(s: str) -> str:
    """移除回复头部信息"""
    return RE_REPLY_HEADER.sub('\n', s)

def remove_quote_lines(s: str) -> str:
    """移除引用行"""
    return RE_QUOTE.sub('', s)

def strip_signature(s: str) -> str:
    """移除签名"""
    parts = RE_SIGNATURE_DELIM.split(s)
    return parts[0] if parts else s

def normalize_unicode(s: str) -> str:
    """Unicode标准化"""
    return unicodedata.normalize('NFKC', s)

def remove_forward_block(s: str) -> str:
    """移除转发块"""
    return RE_FORWARD_BLOCK.sub('\n', s)

def clean_body(raw: str) -> str:
    """
    清理邮件正文内容
    
    【重要修改】：
    为了进行"包含检测"（即判断短邮件内容是否已包含在长邮件的历史记录中），
    我们必须保留引用块(Quotes)、回复头(Reply Headers)和转发块(Forward Blocks)。
    只进行基础的格式化、去HTML和去签名。
    """
    if not raw:
        return ''
    s = raw
    s = normalize_unicode(s)
    s = strip_html(s)
    
    # --- 下面这三行被注释掉，为了保留完整的会话历史 ---
    # s = remove_forward_block(s) 
    # s = remove_reply_headers(s)
    # s = remove_quote_lines(s)
    # ---------------------------------------------

    s = strip_signature(s) # 签名通常不包含在会话逻辑中，可以安全移除
    s = normalize_whitespace(s)
    return s.lower()

def tokens(s: str):
    """
    对文本进行分词处理
    """
    s = normalize_whitespace(s)
    if not s:
        return []
    if CJK_RE.search(s):
        # 中日韩文本处理
        if jieba is not None:
            try:
                return [t for t in jieba.lcut(s) if t.strip()]
            except Exception:
                pass
        if tinysegmenter is not None:
            try:
                return [t for t in tinysegmenter.tokenize(s) if t.strip()]
            except Exception:
                pass
        # 默认分词方法
        out = []
        buf = ''
        for ch in s:
            if '\u4e00' <= ch <= '\u9fff' or ('\u3040' <= ch <= '\u30ff'):
                if buf:
                    out.extend(buf.split())
                    buf = ''
                out.append(ch)
            else:
                buf += ch
        if buf:
            out.extend([t for t in re.sub(r'[^0-9A-Za-z]+', ' ', buf).split() if t.strip()])
        return [t for t in out if t.strip()]
    else:
        # 非CJK文本处理
        # 注意：这里会把 '>' 等标点符号变成空格，这对于忽略引用符号差异非常有帮助
        txt = RE_NON_ALNUM.sub(' ', s)
        return [t for t in txt.split() if t.strip()]

def fuzzy_ratio(a: str, b: str) -> float:
    """计算两个字符串的相似度"""
    return SequenceMatcher(None, a, b).ratio()

# 匹配策略函数
def is_exact_substring(cs: str, cl: str) -> bool:
    """精确子字符串匹配"""
    return cs in cl

def is_token_contiguous_subsequence(cs: str, cl: str) -> bool:
    """
    分词连续子序列匹配
    (容忍空格、换行符和标点符号的差异)
    """
    tcs = tokens(cs)
    tcl = tokens(cl)
    if not tcs:
        return True # 空内容视为匹配
    if not tcl:
        return False
    
    lcs = len(tcs)
    # 如果候选比主串还长，肯定不匹配
    if lcs > len(tcl):
        return False
        
    # 滑动窗口匹配
    for i in range(0, len(tcl) - lcs + 1):
        if tcl[i:i + lcs] == tcs:
            return True
    return False

def is_fuzzy_similar(cs: str, cl: str, threshold: float) -> bool:
    """模糊相似度匹配"""
    return fuzzy_ratio(cs, cl) >= threshold